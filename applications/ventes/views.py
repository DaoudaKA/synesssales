"""Écrans du pilotage commercial."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from applications.comptes.permissions import a_le_droit, peut_consulter, portees
from applications.comptes.services import journaliser

from .formulaires import (
    ActiviteForm,
    ContratForm,
    ObjectifForm,
    ReaffectationForm,
    RefusForm,
    TacheForm,
)
from .models import Affectation, Contrat, Objectif, Prospect, Tache
from .services import (
    avancement,
    commerciaux_cibles,
    contacts_en_double,
    enregistrer_activite,
    planifier_tache,
    reaffecter_prospect,
    refuser_contrat,
    soumettre_contrat,
    terminer_tache,
    valider_contrat,
)
from .tableau_de_bord import indicateurs, prospects_du_tableau, ventilation


@login_required
def liste_prospects(request):
    """Liste des prospects visibles avec les droits de la personne connectée."""
    if not a_le_droit(request.user, "Prospects", "L"):
        raise PermissionDenied
    prospects = Prospect.objects.visible_to(request.user).select_related(
        "produit", "commercial", "equipe"
    )
    contexte = {
        "prospects": prospects,
        # Affiche le lien « Contrats à valider » aux seuls validateurs.
        "peut_valider_contrats": a_le_droit(request.user, "Contrats", "V"),
        "peut_voir_objectifs": peut_consulter(request.user, "Campagnes et objectifs"),
        "peut_voir_tableau": peut_consulter(request.user, "Tableaux de bord"),
    }
    return render(request, "ventes/prospects.html", contexte)


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
        "contrats": prospect.contrats.all(),
        "voir_contrats": a_le_droit(request.user, "Contrats", "L"),
        "peut_soumettre": _peut_agir(request.user, prospect, "C", "Contrats"),
        "peut_valider": bool(portees(request.user, "Contrats", "V")),
    }
    return render(request, "ventes/prospect.html", contexte)


def _peut_agir(utilisateur, prospect, droit, ressource="Activités et relances"):
    """Droit « C » (créer) ou « M » (modifier) d'une ressource, sur un prospect donné.

    Le droit vient de la matrice ; la portée dit sur quels prospects il s'applique.
    """
    etendues = portees(utilisateur, ressource, droit)
    if "toute" in etendues:
        return True
    if "perimetre" in etendues:
        return Prospect.objects.visible_to(utilisateur).filter(pk=prospect.pk).exists()
    # Portée « propre » : seulement les prospects dont on est le commercial.
    return "propre" in etendues and prospect.commercial_id == utilisateur.pk


def _prospect_pour_action(request, pk, droit, ressource="Activités et relances"):
    """Prospect visible par l'utilisateur et sur lequel il a le droit d'agir.

    Hors périmètre : 404 (on ne révèle pas son existence). Sans le droit : 403.
    """
    visibles = Prospect.objects.visible_to(request.user)
    prospect = get_object_or_404(visibles, pk=pk)
    if not _peut_agir(request.user, prospect, droit, ressource):
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


def _peut_valider(utilisateur, contrat):
    """Droit « V » (valider) de la matrice, dans son périmètre, sur un autre que soi."""
    etendues = portees(utilisateur, "Contrats", "V")
    if not etendues:
        return False
    # Séparation des rôles : on ne valide pas le contrat de ses propres prospects.
    if contrat.prospect.commercial_id == utilisateur.pk:
        return False
    if "toute" in etendues:
        return True
    return Prospect.objects.visible_to(utilisateur).filter(pk=contrat.prospect_id).exists()


@login_required
def nouveau_contrat(request, pk):
    """Formulaire de soumission d'un contrat sur un prospect."""
    prospect = _prospect_pour_action(request, pk, "C", "Contrats")
    formulaire = ContratForm(request.POST or None, prospect=prospect)
    if request.method == "POST" and formulaire.is_valid():
        contrat = soumettre_contrat(prospect, formulaire.cleaned_data["date_signature"])
        journaliser(
            request.user,
            "creation",
            "Contrats",
            contrat.pk,
            f"Contrat soumis — « {prospect.nom} »",
        )
        return redirect("prospect", pk=prospect.pk)
    contexte = {
        "titre": "Soumettre un contrat",
        "bouton": "Soumettre à validation",
        "prospect": prospect,
        "formulaire": formulaire,
    }
    return render(request, "ventes/formulaire.html", contexte)


@login_required
def contrats_a_valider(request):
    """Contrats soumis qui attendent une décision, dans le périmètre du validateur."""
    etendues = portees(request.user, "Contrats", "V")
    if not etendues:
        raise PermissionDenied
    contrats = Contrat.objects.filter(
        statut_validation=Contrat.StatutValidation.SOUMIS
    ).select_related("prospect", "prospect__commercial", "prospect__equipe")
    if "toute" not in etendues:
        contrats = contrats.filter(prospect__in=Prospect.objects.visible_to(request.user))
    # Ses propres prospects ne sont pas à valider par soi-même.
    contrats = contrats.exclude(prospect__commercial=request.user)
    return render(request, "ventes/contrats_a_valider.html", {"contrats": contrats})


@login_required
def decision_contrat(request, pk):
    """Examen d'un contrat soumis : validation, ou refus avec motif."""
    contrat = get_object_or_404(
        Contrat.objects.select_related("prospect__commercial", "prospect__equipe"), pk=pk
    )
    if not _peut_valider(request.user, contrat):
        raise PermissionDenied
    formulaire_refus = RefusForm()
    if request.method == "POST":
        # Un contrat déjà décidé est définitif : on ne le redécide pas.
        if contrat.statut_validation != Contrat.StatutValidation.SOUMIS:
            return redirect("contrats_a_valider")
        decision = request.POST.get("decision")
        nom = contrat.prospect.nom
        if decision == "valider":
            valider_contrat(contrat, request.user)
            journaliser(
                request.user, "validation", "Contrats", contrat.pk, f"Contrat validé — « {nom} »"
            )
            return redirect("contrats_a_valider")
        if decision == "refuser":
            formulaire_refus = RefusForm(request.POST)
            if formulaire_refus.is_valid():
                motif = formulaire_refus.cleaned_data["motif"]
                refuser_contrat(contrat, request.user, motif)
                journaliser(
                    request.user,
                    "refus",
                    "Contrats",
                    contrat.pk,
                    f"Contrat refusé — « {nom} » : {motif}",
                )
                return redirect("contrats_a_valider")
        else:
            return HttpResponseBadRequest("Décision inconnue.")
    contexte = {"contrat": contrat, "formulaire_refus": formulaire_refus}
    return render(request, "ventes/contrat.html", contexte)




def _peut_gerer_objectifs(utilisateur, droit):
    """Créer ou modifier un objectif demande la portée « toute » (Responsable commercial)."""
    return "toute" in portees(utilisateur, "Campagnes et objectifs", droit)


@login_required
def liste_objectifs(request):
    """Objectifs visibles, avec la réalisation et le taux d'atteinte."""
    if not peut_consulter(request.user, "Campagnes et objectifs"):
        raise PermissionDenied
    objectifs = Objectif.objects.visible_to(request.user).select_related(
        "produit", "equipe", "commercial"
    )
    lignes = []
    for objectif in objectifs:
        realise, taux = avancement(objectif)
        lignes.append({"objectif": objectif, "realise": realise, "taux": taux})
    contexte = {
        "lignes": lignes,
        "peut_creer": _peut_gerer_objectifs(request.user, "C"),
        "peut_modifier": _peut_gerer_objectifs(request.user, "M"),
    }
    return render(request, "ventes/objectifs.html", contexte)


@login_required
def nouvel_objectif(request):
    """Création d'un objectif (Responsable commercial)."""
    if not _peut_gerer_objectifs(request.user, "C"):
        raise PermissionDenied
    formulaire = ObjectifForm(request.POST or None)
    if request.method == "POST" and formulaire.is_valid():
        objectif = formulaire.save(commit=False)
        objectif.cree_par = request.user
        objectif.save()
        journaliser(
            request.user,
            "creation",
            "Campagnes et objectifs",
            objectif.pk,
            f"Objectif de {objectif.cible} contrats — {objectif.porteur} ({objectif.produit})",
        )
        return redirect("objectifs")
    contexte = {
        "titre": "Nouvel objectif",
        "bouton": "Enregistrer l'objectif",
        "formulaire": formulaire,
    }
    return render(request, "ventes/objectif_formulaire.html", contexte)


@login_required
def modifier_objectif(request, pk):
    """Modification d'un objectif existant (Responsable commercial)."""
    if not _peut_gerer_objectifs(request.user, "M"):
        raise PermissionDenied
    objectif = get_object_or_404(Objectif, pk=pk)
    formulaire = ObjectifForm(request.POST or None, instance=objectif)
    if request.method == "POST" and formulaire.is_valid():
        objectif = formulaire.save()
        journaliser(
            request.user,
            "modification",
            "Campagnes et objectifs",
            objectif.pk,
            f"Objectif de {objectif.cible} contrats — {objectif.porteur} ({objectif.produit})",
        )
        return redirect("objectifs")
    contexte = {
        "titre": "Modifier l'objectif",
        "bouton": "Enregistrer les modifications",
        "formulaire": formulaire,
    }
    return render(request, "ventes/objectif_formulaire.html", contexte)


@login_required
def tableau_commercial(request):
    """Tableau de bord commercial : chiffres clés et résultats comparés."""
    if not peut_consulter(request.user, "Tableaux de bord"):
        raise PermissionDenied
    prospects = prospects_du_tableau(request.user)
    contexte = {
        "indicateurs": indicateurs(prospects, request.user),
        # Chaque entrée : (titre du bloc, lignes de résultats).
        "ventilations": [
            ("Par équipe", ventilation(prospects, "equipe__nom")),
            ("Par produit", ventilation(prospects, "produit__nom")),
            ("Par campagne", ventilation(prospects, "campagne__nom")),
            ("Par zone", ventilation(prospects, "campagne__zone")),
        ],
    }
    return render(request, "ventes/tableau_de_bord.html", contexte)
