"""Tests du moteur de notifications, de l'écran « Mes notifications » et de la cloche."""
import pytest
from django.contrib.auth import get_user_model

from applications.notifications.models import Notification
from applications.notifications.services import notifier

Utilisateur = get_user_model()


@pytest.fixture
def awa(db):
    return Utilisateur.objects.create(email="awa@exemple.com", nom="Awa Diop")


@pytest.fixture
def moussa(db):
    return Utilisateur.objects.create(email="moussa@exemple.com", nom="Moussa Fall")


@pytest.mark.django_db
def test_notifier_cree_une_notification(awa):
    notification, creee = notifier(awa, "essai", "Bonjour", lien="/prospects/")
    assert creee
    assert notification.destinataire == awa
    assert not notification.lue
    assert notification.lien == "/prospects/"


@pytest.mark.django_db
def test_meme_cle_ne_cree_pas_de_doublon(awa):
    premiere, creee1 = notifier(awa, "relance", "En retard", cle="relance-en-retard:1")
    seconde, creee2 = notifier(awa, "relance", "En retard", cle="relance-en-retard:1")
    assert creee1 and not creee2
    assert seconde.pk == premiere.pk
    assert Notification.objects.count() == 1


@pytest.mark.django_db
def test_meme_cle_pour_deux_destinataires_est_permise(awa, moussa):
    notifier(awa, "relance", "En retard", cle="relance-en-retard:1")
    notifier(moussa, "relance", "En retard", cle="relance-en-retard:1")
    assert Notification.objects.count() == 2


@pytest.mark.django_db
def test_sans_cle_chaque_appel_cree_une_notification(awa):
    notifier(awa, "info", "Un")
    notifier(awa, "info", "Deux")
    assert Notification.objects.count() == 2


@pytest.mark.django_db
def test_lien_externe_refuse(awa):
    with pytest.raises(ValueError):
        notifier(awa, "essai", "Piège", lien="https://exemple.com/")
    assert not Notification.objects.exists()


@pytest.mark.django_db
def test_liste_exige_la_connexion(client):
    reponse = client.get("/notifications/")
    assert reponse.status_code == 302
    assert reponse.url.startswith("/connexion/")


@pytest.mark.django_db
def test_liste_montre_seulement_mes_notifications(client, awa, moussa):
    notifier(awa, "info", "Pour Awa seulement")
    notifier(moussa, "info", "Pour Moussa seulement")
    client.force_login(awa)
    contenu = client.get("/notifications/").content.decode()
    assert "Pour Awa seulement" in contenu
    assert "Pour Moussa seulement" not in contenu


@pytest.mark.django_db
def test_non_lues_en_premier(client, awa):
    ancienne, _ = notifier(awa, "info", "Déjà lue")
    ancienne.lue = True
    ancienne.save()
    notifier(awa, "info", "Nouvelle")
    client.force_login(awa)
    contenu = client.get("/notifications/").content.decode()
    assert contenu.index("Nouvelle") < contenu.index("Déjà lue")


@pytest.mark.django_db
def test_marquer_lue_se_fait_en_post(client, awa):
    notification, _ = notifier(awa, "info", "À lire")
    client.force_login(awa)
    adresse = f"/notifications/{notification.pk}/lue/"
    assert client.get(adresse).status_code == 405  # pas de modification par un simple lien
    assert client.post(adresse).status_code == 302
    notification.refresh_from_db()
    assert notification.lue


@pytest.mark.django_db
def test_on_ne_marque_pas_la_notification_d_un_autre(client, awa, moussa):
    notification, _ = notifier(moussa, "info", "Privée")
    client.force_login(awa)
    assert client.post(f"/notifications/{notification.pk}/lue/").status_code == 404
    notification.refresh_from_db()
    assert not notification.lue


@pytest.mark.django_db
def test_tout_marquer_lu_ne_touche_que_les_miennes(client, awa, moussa):
    notifier(awa, "info", "Une")
    notifier(awa, "info", "Deux")
    autre, _ = notifier(moussa, "info", "Pour Moussa")
    client.force_login(awa)
    assert client.post("/notifications/tout-lu/").status_code == 302
    assert not Notification.objects.filter(destinataire=awa, lue=False).exists()
    autre.refresh_from_db()
    assert not autre.lue


@pytest.mark.django_db
def test_la_cloche_affiche_le_nombre_de_non_lues(client, awa):
    notifier(awa, "info", "Une")
    notifier(awa, "info", "Deux")
    client.force_login(awa)
    contenu = client.get("/notifications/").content.decode()
    assert '<span class="pastille">2</span>' in contenu
    client.post("/notifications/tout-lu/")
    contenu = client.get("/notifications/").content.decode()
    assert 'class="pastille"' not in contenu
