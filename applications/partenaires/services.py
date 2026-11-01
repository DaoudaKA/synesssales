"""Services de la collecte : détection des doublons de fiches partenaires."""
import re
import unicodedata
from difflib import SequenceMatcher

from applications.collecte.models import AlerteDoublon

from .models import Partenaire

SEUIL_SIMILARITE = 0.85


def normaliser(texte):
    """Minuscules, sans accents ni ponctuation, espaces réduits."""
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", sans_accents.lower()).strip()


def similarite(nom_a, nom_b):
    """Score de ressemblance entre deux noms, de 0 à 1."""
    return SequenceMatcher(None, normaliser(nom_a), normaliser(nom_b)).ratio()


def villes(partenaire):
    """Villes normalisées de la fiche (celles qui sont renseignées)."""
    candidates = (normaliser(loc.ville) for loc in partenaire.localisations.all())
    return {ville for ville in candidates if ville}


def detecter_doublons(partenaire):
    """Crée une alerte pour chaque fiche trop ressemblante. Retourne les nouvelles alertes."""
    mes_villes = villes(partenaire)
    nouvelles = []
    autres = Partenaire.objects.exclude(pk=partenaire.pk).prefetch_related("localisations")
    for autre in autres:
        score = similarite(partenaire.nom_commercial, autre.nom_commercial)
        if score < SEUIL_SIMILARITE:
            continue
        ses_villes = villes(autre)
        if mes_villes and ses_villes and not (mes_villes & ses_villes):
            continue
        fiche_a, fiche_b = sorted((partenaire, autre), key=lambda fiche: fiche.pk)
        alerte, creee = AlerteDoublon.objects.get_or_create(
            partenaire_a=fiche_a,
            partenaire_b=fiche_b,
            defaults={"score_similarite": round(score, 2)},
        )
        if creee:
            nouvelles.append(alerte)
    return nouvelles
