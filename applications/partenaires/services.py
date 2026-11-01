"""Services de la collecte : détection des doublons de fiches partenaires."""
import re
import unicodedata
from difflib import SequenceMatcher

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from applications.collecte.models import AlerteDoublon, Verification

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
    autres = (
        Partenaire.objects.exclude(pk=partenaire.pk)
        .filter(fusionnee_dans__isnull=True)
        .prefetch_related("localisations")
    )
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



STATUT_APRES_VERIFICATION = {
    Verification.Resultat.CONFORME: Partenaire.StatutVerification.VERIFIE,
    Verification.Resultat.A_CORRIGER: Partenaire.StatutVerification.A_VERIFIER,
    Verification.Resultat.REJETE: Partenaire.StatutVerification.REJETE,
}


@transaction.atomic
def verifier(partenaire, utilisateur, resultat, commentaire=""):
    """Enregistre une vérification et met à jour le statut de la fiche."""
    verification = Verification.objects.create(
        partenaire=partenaire,
        utilisateur=utilisateur,
        resultat=resultat,
        commentaire=commentaire,
    )
    partenaire.statut_verification = STATUT_APRES_VERIFICATION[resultat]
    partenaire.date_derniere_verification = timezone.localdate()
    partenaire.save(
        update_fields=["statut_verification", "date_derniere_verification", "date_modification"]
    )
    return verification




CLES_A_DEDOUBLONNER = {
    "contacts": lambda contact: (contact.type, contact.valeur.strip().lower()),
    "localisations": lambda lieu: (
        normaliser(lieu.pays),
        normaliser(lieu.ville),
        normaliser(lieu.adresse),
    ),
    "services": lambda service: normaliser(service.libelle),
}


def _deplacer_sans_doublon(origine, cible, relation, cle):
    """Déplace vers la cible les éléments qu'elle n'a pas déjà."""
    deja_la = {cle(element) for element in getattr(cible, relation).all()}
    for element in getattr(origine, relation).all():
        if cle(element) not in deja_la:
            element.partenaire = cible
            element.save(update_fields=["partenaire"])
            deja_la.add(cle(element))


@transaction.atomic  # tout ou rien : si une étape échoue, rien n'est modifié
def fusionner(alerte, garder):
    """Fusionne les deux fiches d'une alerte ouverte, sans rien supprimer.

    garder vaut « a » ou « b » : la fiche conservée absorbe l'autre.
    """
    # Une alerte déjà fusionnée ou rejetée ne se traite pas deux fois.
    if alerte.statut != AlerteDoublon.Statut.OUVERTE:
        raise ValueError("Cette alerte est déjà traitée.")
    if garder not in ("a", "b"):
        raise ValueError("La fiche à conserver doit être « a » ou « b ».")
    if garder == "a":
        conservee, absorbee = alerte.partenaire_a, alerte.partenaire_b
    else:
        conservee, absorbee = alerte.partenaire_b, alerte.partenaire_a

    # 1. Contacts, localisations, services : on déplace seulement ce que la
    #    fiche conservée n'a pas déjà, pour ne pas créer de doublons internes.
    for relation, cle in CLES_A_DEDOUBLONNER.items():
        _deplacer_sans_doublon(absorbee, conservee, relation, cle)

    # 2. Provenances, vérifications, prospects : tout passe à la fiche conservée,
    #    car ce sont des historiques à ne jamais perdre.
    for relation in ("provenances", "verifications", "prospects"):
        getattr(absorbee, relation).update(partenaire=conservee)

    # 3. Les champs vides de la fiche conservée sont complétés par l'autre fiche.
    for champ in ("raison_sociale", "description", "categorie"):
        if not getattr(conservee, champ) and getattr(absorbee, champ):
            setattr(conservee, champ, getattr(absorbee, champ))
    conservee.save()

    # 4. La fiche absorbée n'est pas supprimée : on garde un lien vers la
    #    fiche conservée (elle disparaît seulement des listes).
    absorbee.fusionnee_dans = conservee
    absorbee.save(update_fields=["fusionnee_dans", "date_modification"])

    # 5. Les autres alertes ouvertes qui concernaient la fiche absorbée n'ont
    #    plus de sens : on les supprime, puis on relance la détection sur la
    #    fiche conservée pour recréer celles qui restent utiles.
    autres_alertes = AlerteDoublon.objects.filter(statut=AlerteDoublon.Statut.OUVERTE)
    autres_alertes.filter(Q(partenaire_a=absorbee) | Q(partenaire_b=absorbee)).exclude(
        pk=alerte.pk
    ).delete()

    # 6. L'alerte traitée est conservée, marquée « fusionnée » (trace).
    alerte.statut = AlerteDoublon.Statut.FUSIONNEE
    alerte.save(update_fields=["statut"])
    detecter_doublons(conservee)
    return conservee


def rejeter(alerte):
    """Écarte une alerte : les deux fiches sont bien distinctes."""
    if alerte.statut != AlerteDoublon.Statut.OUVERTE:
        raise ValueError("Cette alerte est déjà traitée.")
    alerte.statut = AlerteDoublon.Statut.REJETEE
    alerte.save(update_fields=["statut"])
    return alerte
