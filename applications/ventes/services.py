"""Services du pilotage commercial."""
import datetime
import unicodedata
from difflib import SequenceMatcher

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from applications.comptes.permissions import portees

from .models import Affectation, Contrat, Prospect, ReaffectationProspect, Tache


@transaction.atomic
def affecter(utilisateur, produit, date_debut, campagne=None):
    """Affecte un commercial à un produit, sans perdre l'historique.

    Les affectations encore ouvertes de la personne sont clôturées la veille du
    nouveau début (ou le jour même si elles ont commencé ce jour-là).
    """
    veille = date_debut - datetime.timedelta(days=1)
    ouvertes = Affectation.objects.filter(utilisateur=utilisateur, date_fin__isnull=True)
    for ancienne in ouvertes:
        ancienne.date_fin = max(ancienne.date_debut, veille)
        ancienne.save(update_fields=["date_fin"])
    return Affectation.objects.create(
        utilisateur=utilisateur, produit=produit, campagne=campagne, date_debut=date_debut
    )


def commerciaux_cibles(utilisateur):
    """Commerciaux vers lesquels cette personne peut réaffecter un prospect."""
        # « is_active » est une propriété Python, pas une colonne : on filtre sur « statut ».
    candidats = get_user_model().objects.filter(
        statut="actif", roles__nom="Commercial"
    )
    # Portée « toute » : n'importe quel commercial actif.
    if "toute" in portees(utilisateur, "Prospects", "M"):
        return candidats.distinct()
    # Portée « périmètre » : les équipes qu'elle dirige ou dont elle fait partie.
    condition = Q(equipe__chef_equipe=utilisateur)
    if utilisateur.equipe_id is not None:
        condition |= Q(equipe_id=utilisateur.equipe_id)
    return candidats.filter(condition).distinct()


@transaction.atomic  # tout ou rien : la trace et le changement vont ensemble
def reaffecter_prospect(prospect, nouveau_commercial, auteur, motif=""):
    """Change le commercial d'un prospect en gardant toute la trace.

    Les activités restent rattachées au prospect (elles gardent leur auteur).
    Les tâches encore à faire suivent le nouveau commercial.
    """
    ancien = prospect.commercial
    if nouveau_commercial == ancien:
        raise ValueError("Ce prospect est déjà suivi par ce commercial.")
    trace = ReaffectationProspect.objects.create(
        prospect=prospect,
        ancien_commercial=ancien,
        nouveau_commercial=nouveau_commercial,
        ancienne_equipe=prospect.equipe,
        nouvelle_equipe=nouveau_commercial.equipe,
        auteur=auteur,
        motif=motif,
    )
    prospect.commercial = nouveau_commercial
    prospect.equipe = nouveau_commercial.equipe
    prospect.save(update_fields=["commercial", "equipe"])
    prospect.taches.filter(statut=Tache.Statut.A_FAIRE, responsable=ancien).update(
        responsable=nouveau_commercial
    )
    return trace



# Un prospect gagné, perdu ou refusé n'est plus « en cours » : plus de risque de doublon.
STATUTS_CLOS = [Prospect.Statut.GAGNE, Prospect.Statut.PERDU, Prospect.Statut.REFUSE]
# Même seuil que pour les doublons de partenaires (décision 12).
SEUIL_NOM_PROCHE = 0.85


def _simplifier(texte):
    """Minuscules sans accents, pour comparer « Garage Sénégal » et « garage senegal »."""
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return " ".join(sans_accents.lower().split())


def contacts_en_double(prospect):
    """Autres prospects actifs, suivis par un autre commercial, sur le même client.

    Retourne une liste de couples (prospect, motif). On interroge tous les prospects,
    sans filtre d'équipe : le doublon peut venir d'une autre équipe. Le gabarit
    n'affiche donc que le commercial, l'équipe et le statut, jamais le nom.
    """
    autres = (
        Prospect.objects.filter(produit=prospect.produit, commercial__isnull=False)
        .exclude(pk=prospect.pk)
        .exclude(statut__in=STATUTS_CLOS)
        .exclude(commercial=prospect.commercial)
        .select_related("commercial", "equipe")
    )
    nom = _simplifier(prospect.nom)
    resultats = []
    for autre in autres:
        if prospect.partenaire_id and autre.partenaire_id == prospect.partenaire_id:
            motif = "même partenaire"
        elif SequenceMatcher(None, nom, _simplifier(autre.nom)).ratio() >= SEUIL_NOM_PROCHE:
            motif = "nom très proche"
        else:
            continue
        resultats.append((autre, motif))
    return resultats



@transaction.atomic
def enregistrer_activite(prospect, auteur, activite):
    """Rattache une activité à son prospect et à son auteur.

    La première activité fait passer un prospect « Nouveau » à « Contacté ».
    """
    activite.prospect = prospect
    activite.auteur = auteur
    activite.save()
    if prospect.statut == Prospect.Statut.NOUVEAU:
        prospect.statut = Prospect.Statut.CONTACTE
        prospect.save(update_fields=["statut"])
    return activite


def planifier_tache(prospect, tache):
    """Rattache une tâche au prospect ; elle est confiée à son commercial actuel."""
    tache.prospect = prospect
    tache.responsable = prospect.commercial
    tache.save()
    return tache


def terminer_tache(tache):
    """Marque une tâche comme faite (on garde la ligne, on ne supprime rien)."""
    tache.statut = Tache.Statut.FAITE
    tache.save(update_fields=["statut"])




def soumettre_contrat(prospect, date_signature):
    """Crée un contrat « soumis » : il attend la décision d'un validateur."""
    return Contrat.objects.create(prospect=prospect, date_signature=date_signature)


def _contrat_a_decider(contrat):
    """Verrouille le contrat et vérifie qu'il attend encore une décision.

    Le verrou évite que deux validateurs décident en même temps du même contrat.
    """
    Contrat.objects.select_for_update().get(pk=contrat.pk)
    contrat.refresh_from_db()
    if contrat.statut_validation != Contrat.StatutValidation.SOUMIS:
        raise ValueError("Ce contrat a déjà fait l'objet d'une décision.")


@transaction.atomic
def valider_contrat(contrat, validateur):
    """Valide le contrat ; le prospect devient « Gagné »."""
    _contrat_a_decider(contrat)
    contrat.statut_validation = Contrat.StatutValidation.VALIDE
    contrat.valide_par = validateur  # la personne qui a décidé (validation ou refus)
    contrat.motif_refus = ""
    contrat.save(update_fields=["statut_validation", "valide_par", "motif_refus"])
    prospect = contrat.prospect
    prospect.statut = Prospect.Statut.GAGNE
    prospect.save(update_fields=["statut"])


@transaction.atomic
def refuser_contrat(contrat, validateur, motif):
    """Refuse le contrat avec un motif obligatoire ; le prospect ne change pas de statut."""
    motif = (motif or "").strip()
    if not motif:
        raise ValueError("Un refus doit être motivé.")
    _contrat_a_decider(contrat)
    contrat.statut_validation = Contrat.StatutValidation.REFUSE
    contrat.valide_par = validateur
    contrat.motif_refus = motif
    contrat.save(update_fields=["statut_validation", "valide_par", "motif_refus"])




def realisation(objectif):
    """Nombre de contrats validés qui comptent pour cet objectif.

    On compte les contrats validés, signés pendant la période, sur le produit de
    l'objectif, pour les prospects du commercial (individuel) ou de l'équipe (collectif).
    Le rattachement suit le commercial et l'équipe actuels du prospect.
    """
    contrats = Contrat.objects.filter(
        statut_validation=Contrat.StatutValidation.VALIDE,
        prospect__produit=objectif.produit,
        date_signature__range=(objectif.date_debut, objectif.date_fin),
    )
    if objectif.commercial_id is not None:
        contrats = contrats.filter(prospect__commercial_id=objectif.commercial_id)
    else:
        contrats = contrats.filter(prospect__equipe_id=objectif.equipe_id)
    return contrats.count()


def avancement(objectif):
    """Retourne (réalisé, taux d'atteinte en pourcentage entier)."""
    realise = realisation(objectif)
    return realise, round(100 * realise / objectif.cible)
