"""Services de la collecte : import de fiches partenaires depuis un fichier CSV."""
import csv
import io

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from applications.partenaires.models import (
    Categorie,
    Contact,
    Localisation,
    Partenaire,
    ServicePropose,
)
from applications.partenaires.services import detecter_doublons

from .models import Collecte, Provenance

COLONNE_OBLIGATOIRE = "nom_commercial"

# Colonnes reconnues, avec la longueur maximale acceptée par la base.
LONGUEURS_MAX = {
    "nom_commercial": 200,
    "categorie": 120,
    "pays": 80,
    "region": 80,
    "ville": 80,
    "adresse": 255,
    "telephone": 255,
    "email": 255,
    "service": 200,
}
MAX_LIGNES = 1000
PAYS_PAR_DEFAUT = "Sénégal"


class ImportInvalide(Exception):
    """Le fichier ou la source ne permet pas de lancer l'import."""


def lire_lignes(contenu):
    """Transforme le contenu du fichier (octets) en liste de dictionnaires."""
    try:
        # « utf-8-sig » retire le marqueur ajouté par Excel en début de fichier.
        texte = contenu.decode("utf-8-sig")
    except UnicodeDecodeError as erreur:
        raise ImportInvalide("Le fichier doit être encodé en UTF-8.") from erreur
    lignes = texte.splitlines()
    if not lignes:
        raise ImportInvalide("Le fichier est vide.")
    # Excel en français enregistre avec « ; », les autres outils avec « , ».
    separateur = ";" if ";" in lignes[0] else ","
    lecteur = csv.DictReader(io.StringIO(texte), delimiter=separateur)
    # Les noms de colonnes sont nettoyés : espaces retirés, minuscules.
    lecteur.fieldnames = [(nom or "").strip().lower() for nom in lecteur.fieldnames or []]
    if COLONNE_OBLIGATOIRE not in lecteur.fieldnames:
        raise ImportInvalide(f"La colonne « {COLONNE_OBLIGATOIRE} » est absente du fichier.")
    resultat = list(lecteur)
    if len(resultat) > MAX_LIGNES:
        raise ImportInvalide(f"Le fichier dépasse {MAX_LIGNES} lignes.")
    return resultat


def _creer_fiche(ligne, collecte):
    """Valide une ligne puis crée la fiche, ses éléments et ses provenances."""
    valeurs = {colonne: (ligne.get(colonne) or "").strip() for colonne in LONGUEURS_MAX}
    if not valeurs["nom_commercial"]:
        raise ValidationError("Nom commercial manquant.")
    for colonne, maximum in LONGUEURS_MAX.items():
        if len(valeurs[colonne]) > maximum:
            raise ValidationError(f"« {colonne} » dépasse {maximum} caractères.")
    if valeurs["email"]:
        validate_email(valeurs["email"])  # lève ValidationError si l'adresse est fausse

    categorie = None
    if valeurs["categorie"]:
        categorie, _ = Categorie.objects.get_or_create(nom=valeurs["categorie"])
    fiche = Partenaire.objects.create(
        nom_commercial=valeurs["nom_commercial"], categorie=categorie
    )
    if any(valeurs[c] for c in ("pays", "region", "ville", "adresse")):
        Localisation.objects.create(
            partenaire=fiche,
            pays=valeurs["pays"] or PAYS_PAR_DEFAUT,
            region=valeurs["region"],
            ville=valeurs["ville"],
            adresse=valeurs["adresse"],
        )
    if valeurs["telephone"]:
        Contact.objects.create(
            partenaire=fiche, type=Contact.Type.TELEPHONE, valeur=valeurs["telephone"]
        )
    if valeurs["email"]:
        Contact.objects.create(
            partenaire=fiche, type=Contact.Type.EMAIL, valeur=valeurs["email"]
        )
    if valeurs["service"]:
        ServicePropose.objects.create(partenaire=fiche, libelle=valeurs["service"])

    # Traçabilité : chaque valeur fournie garde sa source et sa collecte.
    for champ, valeur in valeurs.items():
        if valeur:
            Provenance.objects.create(
                partenaire=fiche,
                source=collecte.source,
                collecte=collecte,
                champ=champ,
                valeur=valeur,
                date_collecte=collecte.date_debut,
                niveau=Provenance.Niveau.COLLECTE,
            )
    return fiche


def importer_csv(contenu, source):
    """Importe un fichier CSV. Retourne (collecte, liste des erreurs par ligne)."""
    # Règle du chapitre 4.7 : jamais d'import depuis une source non validée.
    if not source.conditions_validees:
        raise ImportInvalide("Les conditions d'usage de cette source ne sont pas validées.")
    lignes = lire_lignes(contenu)  # avant toute écriture : un fichier invalide ne laisse rien

    collecte = Collecte.objects.create(source=source, date_debut=timezone.now())
    fiches, erreurs = [], []
    # La ligne 1 du fichier contient les en-têtes : les données commencent à la ligne 2.
    for numero, ligne in enumerate(lignes, start=2):
        try:
            # Une transaction par ligne : une ligne en erreur n'annule pas les autres.
            with transaction.atomic():
                fiches.append(_creer_fiche(ligne, collecte))
        except ValidationError as erreur:
            erreurs.append((numero, " ".join(erreur.messages)))

    # La détection se fait après la création de toutes les fiches du fichier.
    for fiche in fiches:
        detecter_doublons(fiche)

    collecte.nb_fiches = len(fiches)
    collecte.nb_erreurs = len(erreurs)
    collecte.date_fin = timezone.now()
    # « En erreur » seulement si rien n'a pu être importé.
    if erreurs and not fiches:
        collecte.statut = Collecte.Statut.EN_ERREUR
    else:
        collecte.statut = Collecte.Statut.TERMINEE
    collecte.save()
    return collecte, erreurs
