"""Services du pilotage commercial."""
import datetime
import unicodedata
from difflib import SequenceMatcher

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from applications.comptes.permissions import portees

from .models import Affectation, Prospect, ReaffectationProspect, Tache


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
