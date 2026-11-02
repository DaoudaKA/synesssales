"""Écrans du pilotage commercial."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from applications.comptes.permissions import a_le_droit, portees
from applications.comptes.services import journaliser

from .formulaires import ActiviteForm, ReaffectationForm, TacheForm
from .models import Affectation, Prospect, Tache
from .services import (
    commerciaux_cibles,
    contacts_en_double,
    enregistrer_activite,
    planifier_tache,
    reaffecter_prospect,
    terminer_tache,
)


@login_required
def liste_prospects(request):
    """Liste des prospects visibles avec les droits de la personne connectée."""
    if not a_le_droit(request.user, "Prospects", "L"):
        raise PermissionDenied
    prospects = Prospect.objects.visible_to(request.user).select_related(
        "produit", "commercial", "equipe"
    )
    return render(request, "ventes/prospects.html", {"prospects": prospects})



@login_required
def liste_affectations(request):
    """Affectations visibles avec les droits de la personne connectée."""
    if not a_le_droit(request.user, "Équipes et affectations", "L"):
        raise PermissionDenied
    affectations = Affectation.objects.visible_to(request.user).select_related(
        "utilisateur", "produit", "campagne"
    )
    return render(request, "ventes/affectations.html", {"affectations": affectations})



def _peut_reaffecter(utilisateur):
    """Réaffecter demande le droit de modifier, hors portée « propre »."""
    return bool(portees(utilisateur, "Prospects", "M") & {"toute", "perimetre"})


@login_required
def fiche_prospect(request, pk):
    """Fiche d'un prospect : informations, historique et réaffectation."""
    if not a_le_droit(request.user, "Prospects", "L"):
        raise PermissionDenied
    # Même filtre que la liste : un prospect hors périmètre est introuvable (404).
    visibles = Prospect.objects.visible_to(request.user).select_related(
        "produit", "commercial", "equipe", "partenaire"
    )
    prospect = get_object_or_404(visibles, pk=pk)

    formulaire = None
    if _peut_reaffecter(request.user):
        formulaire = ReaffectationForm(
            request.POST or None,
            commerciaux=commerciaux_cibles(request.user),
            prospect=prospect,
        )
        if request.method == "POST" and formulaire.is_valid():
            ancien = prospect.commercial
            nouveau = formulaire.cleaned_data["commercial"]
            reaffecter_prospect(
                prospect, nouveau, request.user, formulaire.cleaned_data["motif"]
            )
            journaliser(
                request.user,
                "reaffectation",
                "Prospects",
                prospect.pk,
                f"« {prospect.nom} » : {ancien or 'aucun commercial'} → {nouveau}",
            )
            return redirect("prospect", pk=prospect.pk)
    elif request.method == "POST":
        # Sans le droit de réaffecter, aucune modification n'est acceptée.
        raise PermissionDenied

    contexte = {
        "prospect": prospect,
        "formulaire": formulaire,
        "reaffectations": prospect.reaffectations.select_related(
            "ancien_commercial", "nouveau_commercial", "auteur"
        ),
        "activites": prospect.activites.select_related("auteur")[:10],
        "taches": prospect.taches.filter(statut="a_faire").select_related("responsable"),
        "doublons": contacts_en_double(prospect),
        "peut_consigner": _peut_agir(request.user, prospect, "C"),
        "peut_cloturer": _peut_agir(request.user, prospect, "M"),
    }
    return render(request, "ventes/prospect.html", contexte)




def _peut_agir(utilisateur, prospect, droit):
    """Droit « C » (créer) ou « M » (modifier) sur les activités et relances d'un prospect.

    Le droit vient de la matrice ; la portée dit sur quels prospects il s'applique.
    """
    etendues = portees(utilisateur, "Activités et relances", droit)
    if "toute" in etendues:
        return True
    if "perimetre" in etendues:
        return Prospect.objects.visible_to(utilisateur).filter(pk=prospect.pk).exists()
    # Portée « propre » : seulement les prospects dont on est le commercial.
    return "propre" in etendues and prospect.commercial_id == utilisateur.pk


def _prospect_pour_action(request, pk, droit):
    """Prospect visible par l'utilisateur et sur lequel il a le droit d'agir.

    Hors périmètre : 404 (on ne révèle pas son existence). Sans le droit : 403.
    """
    visibles = Prospect.objects.visible_to(request.user)
    prospect = get_object_or_404(visibles, pk=pk)
    if not _peut_agir(request.user, prospect, droit):
        raise PermissionDenied
    return prospect


@login_required
def nouvelle_activite(request, pk):
    """Formulaire de saisie d'une activité sur un prospect."""
    prospect = _prospect_pour_action(request, pk, "C")
    formulaire = ActiviteForm(request.POST or None)
    if request.method == "POST" and formulaire.is_valid():
        activite = enregistrer_activite(prospect, request.user, formulaire.save(commit=False))
        journaliser(
            request.user,
            "creation",
            "Activités et relances",
            activite.pk,
            f"{activite.get_type_display()} — « {prospect.nom} »",
        )
        return redirect("prospect", pk=prospect.pk)
    contexte = {
        "titre": "Consigner une activité",
        "bouton": "Enregistrer l'activité",
        "prospect": prospect,
        "formulaire": formulaire,
    }
    return render(request, "ventes/formulaire.html", contexte)


@login_required
def nouvelle_tache(request, pk):
    """Formulaire de planification d'une relance sur un prospect."""
    prospect = _prospect_pour_action(request, pk, "C")
    formulaire = TacheForm(request.POST or None)
    if request.method == "POST" and formulaire.is_valid():
        tache = planifier_tache(prospect, formulaire.save(commit=False))
        journaliser(
            request.user,
            "creation",
            "Activités et relances",
            tache.pk,
            f"{tache.get_type_display()} prévue pour « {prospect.nom} »",
        )
        return redirect("prospect", pk=prospect.pk)
    contexte = {
        "titre": "Planifier une relance",
        "bouton": "Planifier",
        "prospect": prospect,
        "formulaire": formulaire,
    }
    return render(request, "ventes/formulaire.html", contexte)


@login_required
@require_POST  # une action qui modifie des données ne se fait jamais par simple lien
def tache_faite(request, pk):
    """Marque une tâche comme faite."""
    tache = get_object_or_404(Tache, pk=pk)
    prospect = _prospect_pour_action(request, tache.prospect_id, "M")
    if tache.statut == Tache.Statut.A_FAIRE:
        terminer_tache(tache)
        journaliser(
            request.user,
            "modification",
            "Activités et relances",
            tache.pk,
            f"{tache.get_type_display()} terminée — « {prospect.nom} »",
        )
    # Le bouton existe sur la fiche et sur « Mes relances » : on revient d'où l'on vient.
    if request.POST.get("retour") == "relances":
        return redirect("relances")
    return redirect("prospect", pk=prospect.pk)


@login_required
def mes_relances(request):
    """Mes tâches à faire, les plus urgentes en premier (ordre de l'échéance)."""
    if not a_le_droit(request.user, "Activités et relances", "L"):
        raise PermissionDenied
    taches = Tache.objects.filter(
        responsable=request.user, statut=Tache.Statut.A_FAIRE
    ).select_related("prospect")
    contexte = {
        "taches": taches,
        "maintenant": timezone.now(),  # sert à repérer les retards dans le gabarit
        "peut_cloturer": bool(portees(request.user, "Activités et relances", "M")),
    }
    return render(request, "ventes/relances.html", contexte)
