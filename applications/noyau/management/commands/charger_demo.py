"""Commande : crée des données de démonstration (profils, équipes, prospects).

À utiliser en développement seulement, jamais en production.
"""
import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from applications.comptes.matrice import charger_matrice
from applications.comptes.models import Role
from applications.equipes.models import Equipe
from applications.partenaires.models import Categorie, Localisation, Partenaire
from applications.ventes.models import Produit, Prospect
from applications.ventes.services import affecter

Utilisateur = get_user_model()

EQUIPES = ["Équipe Dakar", "Équipe Thiès"]

# (e-mail, nom, rôle, équipe)
PROFILS = [
    ("commercial1@exemple.com", "Awa Diop", "Commercial", "Équipe Dakar"),
    ("commercial2@exemple.com", "Moussa Fall", "Commercial", "Équipe Dakar"),
    ("commercial3@exemple.com", "Fatou Ndiaye", "Commercial", "Équipe Thiès"),
    ("chef@exemple.com", "Ibou Sarr", "Chef d'équipe", "Équipe Dakar"),
    ("data@exemple.com", "Aminata Ba", "Responsable data", None),
]

# (nom du prospect, e-mail du commercial, équipe)
PROSPECTS = [
    ("Garage Baobab", "commercial1@exemple.com", "Équipe Dakar"),
    ("Auto Teranga", "commercial1@exemple.com", "Équipe Dakar"),
    ("Pièces Sahel", "commercial2@exemple.com", "Équipe Dakar"),
    ("Mécanique Lac Rose", "commercial2@exemple.com", "Équipe Dakar"),
    ("Garage Thiès Centre", "commercial3@exemple.com", "Équipe Thiès"),
    ("Casse Auto Rufisque", None, None),
]


class Command(BaseCommand):
    help = "Crée des comptes, équipes et prospects de démonstration."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mot-de-passe",
            dest="mot_de_passe",
            required=True,
            help="Mot de passe commun des comptes de démonstration.",
        )

    def handle(self, *args, **options):
        charger_matrice()
        produit, _ = Produit.objects.get_or_create(nom="Garage.sn")
        equipes = {nom: Equipe.objects.get_or_create(nom=nom)[0] for nom in EQUIPES}
        utilisateurs = {}
        for email, nom, role, nom_equipe in PROFILS:
            utilisateur, _ = Utilisateur.objects.get_or_create(
                email=email, defaults={"nom": nom}
            )
            utilisateur.nom = nom
            utilisateur.equipe = equipes.get(nom_equipe)
            utilisateur.set_password(options["mot_de_passe"])
            utilisateur.save()
            utilisateur.roles.set([Role.objects.get(nom=role)])
            utilisateurs[email] = utilisateur
        dakar = equipes["Équipe Dakar"]
        dakar.chef_equipe = utilisateurs["chef@exemple.com"]
        dakar.save()
        for nom, email, nom_equipe in PROSPECTS:
            Prospect.objects.update_or_create(
                nom=nom,
                defaults={
                    "produit": produit,
                    "commercial": utilisateurs.get(email),
                    "equipe": equipes.get(nom_equipe),
                },
            )

        assurance, _ = Produit.objects.get_or_create(nom="Assurance auto")
        for email, utilisateur in utilisateurs.items():
            est_commercial = utilisateur.roles.filter(nom="Commercial").exists()
            if est_commercial and not utilisateur.affectations.exists():
                if email == "commercial1@exemple.com":
                    affecter(utilisateur, assurance, datetime.date(2026, 1, 1))
                affecter(utilisateur, produit, datetime.date(2026, 7, 1))
        garage, _ = Categorie.objects.get_or_create(nom="Garage automobile")
        fiches = [
            ("Garage Teranga", "Dakar", Partenaire.StatutVerification.VERIFIE),
            ("Auto Service Thiès", "Thiès", Partenaire.StatutVerification.A_VERIFIER),
            ("Carrosserie Almadies", "Dakar", Partenaire.StatutVerification.A_VERIFIER),
        ]
        for nom, ville, statut in fiches:
            fiche, cree = Partenaire.objects.get_or_create(
                nom_commercial=nom,
                defaults={"categorie": garage, "statut_verification": statut},
            )
            if cree:
                Localisation.objects.create(partenaire=fiche, pays="Sénégal", ville=ville)

        self.stdout.write(self.style.SUCCESS("Données de démonstration chargées."))
