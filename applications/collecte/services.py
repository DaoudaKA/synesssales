"""Services de la collecte : import de fiches partenaires depuis un fichier CSV."""
import csv
import io
import json

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

from .models import Collecte, LigneRejetee, Provenance

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


class SourceNonAutorisee(ImportInvalide):
    """La source n'a pas été validée par SYNESS : aucune collecte n'est permise."""


def verifier_source_autorisee(source):
    """Garde centrale : tout import ou connecteur doit l'appeler avant de commencer.

    Règle du chapitre 4.7 : jamais de collecte depuis une source non validée.
    """
    if not source.conditions_validees:
        raise SourceNonAutorisee("Les conditions d'usage de cette source ne sont pas validées.")


def valider_source(source, utilisateur, reference):
    """Enregistre la validation de SYNESS : qui, quand et sur quelle base.

    La référence du document est obligatoire : sans trace, pas de validation.
    """
    reference = (reference or "").strip()
    if not reference:
        raise ValueError("La référence du document de validation est obligatoire.")
    source.conditions_validees = True
    source.validee_par = utilisateur
    source.date_validation = timezone.localdate()
    source.reference_validation = reference
    source.save(
        update_fields=[
            "conditions_validees",
            "validee_par",
            "date_validation",
            "reference_validation",
        ]
    )
    return source


def revoquer_source(source, motif):
    """Retire l'autorisation. La trace de la dernière validation est conservée."""
    if not (motif or "").strip():
        raise ValueError("Une révocation doit être motivée.")
    source.conditions_validees = False
    source.save(update_fields=["conditions_validees"])
    return source


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

def _est_incomplete(ligne):
    """Une fiche est incomplète si elle n'a aucun moyen de contact ou aucune ville."""

    def valeur(colonne):
        return (ligne.get(colonne) or "").strip()

    sans_contact = not valeur("telephone") and not valeur("email")
    return sans_contact or not valeur("ville")


def _apercu(ligne):
    """Contenu de la ligne rejetée, tronqué à 500 caractères pour le journal."""
    return json.dumps(ligne, ensure_ascii=False, default=str)[:500]



def traiter_lignes(lignes, source, version_connecteur=""):
    """Pipeline commun à l'import de fichier et aux connecteurs.

    Crée la collecte, une fiche par ligne valide (avec sa provenance), journalise chaque
    ligne rejetée, compte les fiches incomplètes, puis détecte les doublons.
    Retourne (collecte, liste des erreurs par ligne).
    """
    collecte = Collecte.objects.create(
        source=source, date_debut=timezone.now(), version_connecteur=version_connecteur
    )
    fiches, erreurs, incompletes = [], [], 0
    # La ligne 1 du fichier contient les en-têtes : les données commencent à la ligne 2.
    for numero, ligne in enumerate(lignes, start=2):
        try:
            # Une transaction par ligne : une ligne en erreur n'annule pas les autres.
            with transaction.atomic():
                fiches.append(_creer_fiche(ligne, collecte))
            if _est_incomplete(ligne):
                incompletes += 1
        except ValidationError as erreur:
            motif = " ".join(erreur.messages)
            erreurs.append((numero, motif))
            # Journal détaillé : la ligne refusée reste consultable après la collecte.
            LigneRejetee.objects.create(
                collecte=collecte, numero=numero, motif=motif[:300], contenu=_apercu(ligne)
            )

    # La détection se fait après la création de toutes les fiches de la collecte.
    doublons = 0
    for fiche in fiches:
        doublons += len(detecter_doublons(fiche))

    collecte.nb_fiches = len(fiches)
    collecte.nb_erreurs = len(erreurs)
    collecte.nb_incomplets = incompletes
    collecte.nb_doublons = doublons
    collecte.date_fin = timezone.now()
    # « En erreur » seulement si rien n'a pu être importé.
    if erreurs and not fiches:
        collecte.statut = Collecte.Statut.EN_ERREUR
    else:
        collecte.statut = Collecte.Statut.TERMINEE
    collecte.save()
    return collecte, erreurs


def importer_csv(contenu, source):
    """Importe un fichier CSV. Retourne (collecte, liste des erreurs par ligne)."""
    # Règle du chapitre 4.7 : jamais d'import depuis une source non validée.
    verifier_source_autorisee(source)
    lignes = lire_lignes(contenu)  # avant toute écriture : un fichier invalide ne laisse rien
    return traiter_lignes(lignes, source)
