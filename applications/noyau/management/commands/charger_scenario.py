"""Commande : ajoute à la démonstration les données du scénario de présentation.

Elle exécute d'abord « charger_demo » (comptes, équipes, prospects, partenaires), puis
ajoute le Responsable commercial, des activités, des relances, des contrats et des
objectifs. Elle peut être relancée sans créer de doublons.

Elle est séparée de « charger_demo » car de nombreux tests supposent que les prospects
de démonstration n'ont encore ni activité, ni contrat, ni objectif.
À utiliser en développement seulement, jamais en production.
"""
import datetime

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from applications.comptes.models import Role
from applications.equipes.models import Equipe
from applications.partenaires.models import Partenaire
from applications.ventes.models import Activite, Objectif, Produit, Prospect, Tache
from applications.ventes.services import refuser_contrat, soumettre_contrat, valider_contrat

Utilisateur = get_user_model()

# Statut de départ des prospects, pour que la démonstration ressemble à un vrai pipeline.
STATUTS = {
    "Garage Baobab": Prospect.Statut.QUALIFIE,
    "Auto Teranga": Prospect.Statut.PROPOSITION,
    "Pièces Sahel": Prospect.Statut.PROPOSITION,
    "Mécanique Lac Rose": Prospect.Statut.PROPOSITION,
    "Garage Thiès Centre": Prospect.Statut.PROPOSITION,
}


class Command(BaseCommand):
    help = "Charge les données du scénario de démonstration (à lancer après charger_demo)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mot-de-passe",
            dest="mot_de_passe",
            required=True,
            help="Mot de passe commun des comptes de démonstration.",
        )

    def handle(self, *args, **options):
        # Les comptes, équipes, prospects et partenaires de base.
        call_command("charger_demo", mot_de_passe=options["mot_de_passe"])

        maintenant = timezone.now()
        aujourdhui = timezone.localdate()
        produit = Produit.objects.get(nom="Garage.sn")
        dakar = Equipe.objects.get(nom="Équipe Dakar")
        thies = Equipe.objects.get(nom="Équipe Thiès")
        awa = Utilisateur.objects.get(email="commercial1@exemple.com")
        moussa = Utilisateur.objects.get(email="commercial2@exemple.com")
        fatou = Utilisateur.objects.get(email="commercial3@exemple.com")

        responsable = self.creer_responsable(options["mot_de_passe"])
        self.preparer_prospects(produit, thies, fatou)
        self.creer_activites_et_relances(awa, maintenant)
        self.creer_contrats(responsable, aujourdhui)
        self.creer_objectifs(
            produit,
            responsable,
            aujourdhui,
            [(dakar, moussa, 2), (dakar, None, 4), (thies, fatou, 3)],
        )

        self.stdout.write(self.style.SUCCESS("Scénario de démonstration chargé."))
        self.stdout.write(
            "Comptes : commercial1/2/3, chef, data, responsable (@exemple.com)."
        )

    def creer_responsable(self, mot_de_passe):
        """Le Responsable commercial : valide les contrats et fixe les objectifs."""
        responsable, _ = Utilisateur.objects.get_or_create(
            email="responsable@exemple.com", defaults={"nom": "Mariama Diallo"}
        )
        responsable.nom = "Mariama Diallo"
        responsable.set_password(mot_de_passe)
        responsable.save()
        responsable.roles.set([Role.objects.get(nom="Responsable commercial")])
        return responsable

    def preparer_prospects(self, produit, thies, fatou):
        """Statuts de départ, et deux prospects de deux équipes sur le même partenaire."""
        for nom, statut in STATUTS.items():
            # Seulement si le prospect est encore « nouveau » : on ne défait rien.
            Prospect.objects.filter(nom=nom, statut=Prospect.Statut.NOUVEAU).update(statut=statut)
        teranga = Partenaire.objects.get(nom_commercial="Garage Teranga")
        # Le même client suivi par deux commerciaux : déclenche le contact multiple.
        Prospect.objects.filter(nom="Garage Baobab").update(partenaire=teranga)
        Prospect.objects.get_or_create(
            nom="Teranga Auto Thiès",
            defaults={
                "produit": produit,
                "commercial": fatou,
                "equipe": thies,
                "partenaire": teranga,
                "statut": Prospect.Statut.CONTACTE,
            },
        )

    def creer_activites_et_relances(self, awa, maintenant):
        """Quelques interactions passées et des relances, dont une en retard."""
        baobab = Prospect.objects.get(nom="Garage Baobab")
        auto_teranga = Prospect.objects.get(nom="Auto Teranga")
        jour = datetime.timedelta(days=1)
        if not baobab.activites.exists():
            Activite.objects.create(
                prospect=baobab,
                auteur=awa,
                type=Activite.Type.APPEL,
                date=maintenant - 4 * jour,
                duree_minutes=12,
                resultat="Intéressé, demande une démonstration",
                objections="Craint le coût de l'abonnement",
            )
            Activite.objects.create(
                prospect=baobab,
                auteur=awa,
                type=Activite.Type.VISITE,
                date=maintenant - 1 * jour,
                resultat="Présentation faite au gérant",
            )
        if not auto_teranga.activites.exists():
            Activite.objects.create(
                prospect=auto_teranga,
                auteur=awa,
                type=Activite.Type.MESSAGE,
                date=maintenant - 2 * jour,
                resultat="Message envoyé, en attente de réponse",
            )
        if not Tache.objects.filter(prospect__in=[baobab, auto_teranga]).exists():
            # Une relance en retard (échéance dépassée), pour montrer l'alerte.
            Tache.objects.create(
                prospect=baobab,
                responsable=awa,
                type=Tache.Type.RELANCE,
                echeance=maintenant - 2 * jour,
            )
            Tache.objects.create(
                prospect=baobab,
                responsable=awa,
                type=Tache.Type.RENDEZ_VOUS,
                echeance=maintenant + 2 * jour,
            )
            Tache.objects.create(
                prospect=auto_teranga,
                responsable=awa,
                type=Tache.Type.PROPOSITION,
                echeance=maintenant + 1 * jour,
            )

    def creer_contrats(self, responsable, aujourdhui):
        """Deux contrats à valider, un validé et un refusé avec motif.

        « Garage Baobab » n'en a aucun : on peut en soumettre un en direct.
        """
        signature = aujourdhui - datetime.timedelta(days=5)
        for nom, decision in [
            ("Auto Teranga", "a_valider"),
            ("Pièces Sahel", "a_valider"),
            ("Mécanique Lac Rose", "valide"),
            ("Garage Thiès Centre", "refuse"),
        ]:
            prospect = Prospect.objects.get(nom=nom)
            if prospect.contrats.exists():
                continue
            contrat = soumettre_contrat(prospect, signature)
            if decision == "valide":
                valider_contrat(contrat, responsable)
            elif decision == "refuse":
                refuser_contrat(contrat, responsable, "Pièces justificatives manquantes")

    def creer_objectifs(self, produit, responsable, aujourdhui, objectifs):
        """Objectifs individuels et collectif, sur une période qui contient « aujourd'hui »."""
        debut = aujourdhui - datetime.timedelta(days=60)
        fin = aujourdhui + datetime.timedelta(days=30)
        for equipe, commercial, cible in objectifs:
            existe = Objectif.objects.filter(
                produit=produit, equipe=equipe, commercial=commercial
            ).exists()
            if not existe:
                Objectif.objects.create(
                    produit=produit,
                    equipe=equipe,
                    commercial=commercial,
                    cible=cible,
                    date_debut=debut,
                    date_fin=fin,
                    cree_par=responsable,
                )
