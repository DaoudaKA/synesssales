"""Écrans de la collecte : fiches partenaires."""
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from applications.collecte.models import AlerteDoublon
from applications.comptes.permissions import a_le_droit, peut_consulter
from applications.comptes.services import journaliser

from .formulaires import PartenaireForm, VerificationForm
from .models import Partenaire
from .services import detecter_doublons, fusionner, rejeter, verifier


@login_required
def liste_partenaires(request):
    """Liste des fiches visibles, avec recherche et filtre de vérification."""
    if not peut_consulter(request.user, "Fiches partenaires"):
        raise PermissionDenied
    terme = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "")
    partenaires = (
        Partenaire.objects.visible_to(request.user)
        .rechercher(terme)
        .select_related("categorie")
        .prefetch_related("localisations")
    )
    if statut in Partenaire.StatutVerification.values:
        partenaires = partenaires.filter(statut_verification=statut)
    contexte = {
        "partenaires": partenaires,
        "terme": terme,
        "statut": statut,
        "statuts": Partenaire.StatutVerification.choices,
        "peut_creer": a_le_droit(request.user, "Fiches partenaires", "C"),
        "peut_valider": a_le_droit(request.user, "Fiches partenaires", "V"),
    }
    return render(request, "partenaires/liste.html", contexte)



@login_required
def nouveau_partenaire(request):
    """Saisie d'une fiche : réservée au droit de création de la matrice."""
    if not a_le_droit(request.user, "Fiches partenaires", "C"):
        raise PermissionDenied
    formulaire = PartenaireForm(request.POST or None)
    if request.method == "POST" and formulaire.is_valid():
        partenaire = formulaire.enregistrer()
        alertes = detecter_doublons(partenaire)
        detail = f"Création de la fiche « {partenaire.nom_commercial} »"
        if alertes:
            detail += f" ({len(alertes)} doublon(s) suspecté(s))"
        journaliser(request.user, "creation", "Fiches partenaires", partenaire.pk, detail)
        if alertes and a_le_droit(request.user, "Fiches partenaires", "V"):
            return redirect("doublons")
        return redirect(f"{reverse('partenaires')}?{urlencode({'q': partenaire.nom_commercial})}")
    return render(request, "partenaires/formulaire.html", {"formulaire": formulaire})


@login_required
def liste_doublons(request):
    """Alertes de doublon encore ouvertes : réservé au droit de validation."""
    if not a_le_droit(request.user, "Fiches partenaires", "V"):
        raise PermissionDenied
    alertes = AlerteDoublon.objects.filter(
        statut=AlerteDoublon.Statut.OUVERTE
    ).select_related("partenaire_a", "partenaire_b")
    return render(request, "partenaires/doublons.html", {"alertes": alertes})




@login_required
def verifier_partenaire(request, pk):
    """Contrôle d'une fiche : réservé au droit de validation de la matrice."""
    if not a_le_droit(request.user, "Fiches partenaires", "V"):
        raise PermissionDenied
    partenaire = get_object_or_404(Partenaire, pk=pk)
    formulaire = VerificationForm(request.POST or None)
    if request.method == "POST" and formulaire.is_valid():
        verification = verifier(
            partenaire,
            request.user,
            formulaire.cleaned_data["resultat"],
            formulaire.cleaned_data["commentaire"],
        )
        journaliser(
            request.user,
            "verification",
            "Fiches partenaires",
            partenaire.pk,
                       f"Vérification de « {partenaire.nom_commercial} » : "
            f"{verification.get_resultat_display()}",
        )
        return redirect(f"{reverse('partenaires')}?{urlencode({'q': partenaire.nom_commercial})}")
    contexte = {
        "partenaire": partenaire,
        "formulaire": formulaire,
        "verifications": partenaire.verifications.select_related("utilisateur"),
    }
    return render(request, "partenaires/verification.html", contexte)




def _alerte_ouverte_a_traiter(request, pk):
    """Contrôle le droit de validation et retourne l'alerte encore ouverte."""
    if not a_le_droit(request.user, "Fiches partenaires", "V"):
        raise PermissionDenied
    return get_object_or_404(
        AlerteDoublon.objects.select_related("partenaire_a", "partenaire_b"),
        pk=pk,
        statut=AlerteDoublon.Statut.OUVERTE,
    )


@login_required
@require_POST
def rejeter_doublon(request, pk):
    """L'alerte est écartée : les deux fiches restent distinctes."""
    alerte = _alerte_ouverte_a_traiter(request, pk)
    rejeter(alerte)
    journaliser(
        request.user, "rejet_doublon", "Fiches partenaires", alerte.pk, f"Doublon écarté : {alerte}"
    )
    return redirect("doublons")


@login_required
@require_POST
def fusionner_doublon(request, pk):
    """Fusionne les deux fiches en gardant celle choisie (« a » ou « b »)."""
    alerte = _alerte_ouverte_a_traiter(request, pk)
    garder = request.POST.get("conservee")
    if garder not in ("a", "b"):
        return HttpResponseBadRequest("Fiche à conserver invalide.")
    absorbee = alerte.partenaire_b if garder == "a" else alerte.partenaire_a
    conservee = fusionner(alerte, garder)
    journaliser(
        request.user,
        "fusion",
        "Fiches partenaires",
        conservee.pk,
        f"« {absorbee.nom_commercial} » fusionnée dans « {conservee.nom_commercial} »",
    )
    return redirect("doublons")
