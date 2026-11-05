"""Connecteurs de collecte : interface commune, registre et lancement d'une collecte.

Un connecteur sait récupérer les données d'UNE source et les transformer en lignes au
même format que l'import CSV (nom_commercial, ville, telephone...). Tout le reste
(validation, doublons, provenance) est commun et se trouve dans `traiter_lignes`.
"""
import time

from django.utils import timezone

from .models import Collecte
from .services import (
    MAX_LIGNES,
    ImportInvalide,
    traiter_lignes,
    verifier_source_autorisee,
)

# Registre : code du connecteur → classe.
CONNECTEURS = {}


def enregistrer(classe):
    """Décorateur : inscrit un connecteur dans le registre sous son code."""
    CONNECTEURS[classe.code_source] = classe
    return classe


class BaseConnecteur:
    """Interface que tout connecteur doit respecter."""

    code_source = ""  # identifiant du connecteur, saisi dans la fiche de la source
    delai_secondes = 1.0  # délai minimal entre deux requêtes (limite de débit)
    version = "1"  # version du connecteur, conservée dans chaque collecte

    def __init__(self):
        self._dernier_appel = None

    def espacer(self):
        """À appeler avant chaque requête : attend le délai minimal depuis la précédente."""
        if self._dernier_appel is not None:
            attente = self.delai_secondes - (time.monotonic() - self._dernier_appel)
            if attente > 0:
                time.sleep(attente)
        self._dernier_appel = time.monotonic()

    def recuperer(self):
        """Produit les données brutes de la source."""
        raise NotImplementedError

    def analyser(self, brut):
        """Transforme les données brutes en liste de dictionnaires (une ligne par fiche)."""
        raise NotImplementedError


@enregistrer
class ConnecteurDemonstration(BaseConnecteur):
    """Connecteur FICTIF : aucune donnée réelle, aucun accès réseau.

    Sert aux tests et à la démonstration du mécanisme. Une vraie source aura son propre
    connecteur, écrit seulement après la validation écrite de SYNESS.
    """

    code_source = "demonstration"
    delai_secondes = 0
    version = "1.0"

    def recuperer(self):
        return [
            ("Atelier Fictif Un", "Dakar"),
            ("Garage Fictif Deux", "Thiès"),
            ("Carrosserie Fictive Trois", "Saint-Louis"),
        ]

    def analyser(self, brut):
        return [
            {"nom_commercial": nom, "ville": ville, "pays": "Sénégal"} for nom, ville in brut
        ]


def lancer_collecte(source):
    """Lance la collecte d'une source par son connecteur. Retourne (collecte, erreurs).

    - refusée AVANT toute action si la source n'est pas autorisée (SourceNonAutorisee) ;
    - refusée si aucun connecteur n'est associé à la source ;
    - un échec de récupération est ENREGISTRÉ (collecte « en erreur » et son message) au
      lieu de faire planter l'appelant : relances et notification en dépendent.
    """
    verifier_source_autorisee(source)
    classe = CONNECTEURS.get(source.code_connecteur)
    if classe is None:
        raise ImportInvalide("Aucun connecteur n'est associé à cette source.")

    connecteur = classe()
    try:
        lignes = connecteur.analyser(connecteur.recuperer())
        if len(lignes) > MAX_LIGNES:
            raise ImportInvalide(f"La collecte dépasse {MAX_LIGNES} lignes.")
    except Exception as erreur:  # noqa: BLE001 - toute panne de collecte est à consigner
        maintenant = timezone.now()
        collecte = Collecte.objects.create(
            source=source,
            date_debut=maintenant,
            date_fin=maintenant,
            statut=Collecte.Statut.EN_ERREUR,
            version_connecteur=connecteur.version,
            message_erreur=str(erreur)[:500],
        )
        return collecte, [(0, str(erreur))]
    return traiter_lignes(lignes, source, version_connecteur=connecteur.version)
