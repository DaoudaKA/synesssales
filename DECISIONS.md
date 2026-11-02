# Journal des décisions

Ce fichier garde la trace des décisions du projet : quoi, quand, qui, et avec quelles conséquences. Les décisions marquées « à valider » restent des propositions tant que SYNESS ne les a pas confirmées par écrit.

| N° | Date | Décision | Décideur | Statut | Conséquence |
|----|------|----------|----------|--------|-------------|
| 1 | 2026-10-30 | Technologies : Python, Django, PostgreSQL, Redis, Docker | Daouda KA (proposition) | À valider par M. Sy | Pile du plan, section 3 |
| 2 | 2026-10-30 | Noms en français pour le code du projet : dossier `configuration/` au lieu de `config/`, dossier `applications/` au lieu de `apps/` | Daouda KA | À valider par M. Sy | Écart avec la structure du plan (section 2.4), pour faciliter la lecture par SYNESS |
| 3 | 2026-10-30 | Les noms imposés par Django restent en anglais (`views.py`, `urls.py`, `models.py`, `apps.py`) | Daouda KA | Décidé | Django cherche ces noms exacts ; les renommer casserait le projet |
| 4 | 2026-10-30 | Un fichier à la fois, un commit par étape | Daouda KA | Décidé | Historique Git lisible, en ligne avec la boucle de travail du plan (section 8.1) |
| 5 | 2026-10-30 | PostgreSQL installé directement sur le poste de développement ; Docker prévu pour la livraison | Daouda KA | Décidé | Docker sera validé avant le jalon 9 |
| 6 | 2026-10-30 | Première adresse du projet : `/sante/`, qui répond `{"statut": "ok"}` | Daouda KA | Décidé | Permet à Docker et à la supervision de vérifier que l'application tourne |

## Décisions en attente de SYNESS

- Hébergement (VPS ou hébergement existant de SYNESS)
- Première source de collecte
- Mode d'accès à Garage.sn
- Cadre de collaboration (statut, durée, rémunération, propriété du code)




## 2026-10-30

- PostgreSQL 18 installé en direct sur le poste de développement. La CI et le plan utilisent la 16 : à aligner avant la livraison.
- Utilisateur personnalisé (connexion par e-mail) déclaré avant les premières migrations métier, car le changer ensuite est très coûteux.
- `PermissionMetier` : nom choisi pour ne pas confondre avec la `Permission` interne de Django.
- Un compte suspendu ne peut pas se connecter (`is_active` dérivé du statut).
- `SECURE_HSTS_PRELOAD` non activé : décision irréversible, à prendre quand le domaine de production existe.
- Suppression d'un chef d'équipe ou d'une équipe : pas de suppression en cascade (`SET_NULL`), pour ne perdre ni équipe ni utilisateur.


| 7 | 2026-10-30 | PostgreSQL 18 installé sur le poste de développement ; PostgreSQL 16 pour la CI et Docker | Daouda KA | Décidé | À aligner avant la livraison |
| 8 | 2026-10-30 | Utilisateur personnalisé (connexion par e-mail), déclaré avant les premières migrations métier | Daouda KA | Décidé | Changer de modèle utilisateur plus tard serait très coûteux |
| 9 | 2026-10-30 | `PermissionMetier` : nom choisi pour ne pas confondre avec la `Permission` interne de Django | Daouda KA | Décidé | Matrice de l'annexe G à charger dans ce modèle (jalon 1) |
| 10 | 2026-10-30 | Un compte suspendu ne peut pas se connecter (`is_active` dérivé du statut) | Daouda KA | Décidé | |
| 11 | 2026-10-30 | `SECURE_HSTS_PRELOAD` non activé | Daouda KA | Décidé | Irréversible : à décider quand le domaine de production existe |
| 12 | 2026-10-31 | Suppression d'un chef d'équipe ou d'une équipe : pas de suppression en cascade (`SET_NULL`) | Daouda KA | Décidé | On ne perd ni équipe ni utilisateur |
| 13 | 2026-10-31 | `PROTECT` sur les sources, produits, prospects et contrats | Daouda KA | Décidé | Une donnée référencée ne peut pas être supprimée par erreur : traçabilité |
| 14 | 2026-10-31 | Une affectation terminée garde sa date de fin au lieu d'être supprimée | Daouda KA | Décidé | Conserve l'historique (cahier des charges, 6.4) |
| 15 | 2026-10-31 | Un enregistrement vocal sans consentement est refusé par la base de données | Daouda KA | À valider par M. Sy | Dépend de la téléphonie et de la conformité (cahier des charges, chapitre 8) |
| 16 | 2026-10-31 | Journal d'audit : modification et suppression d'une entrée interdites dans le modèle | Daouda KA | Décidé | Protection de base, à renforcer au jalon 1 (les opérations en masse ne sont pas bloquées) |
| 17 | 2026-10-31 | Type de notification en texte libre | Daouda KA | Décidé | La liste des événements reste à valider avec SYNESS |
| 18 | 2026-10-31 | Python 3.12 dans l'image Docker | Daouda KA | Décidé | Version visée par ruff et par le plan ; Django 5.2 la supporte |

| 19 | 2026-10-31 | Les droits viennent uniquement des rôles : un compte administrateur Django n'a pas de droit métier automatique, un compte suspendu n'en a aucun | Daouda KA | Décidé | La matrice reste la seule source de vérité |
| 20 | 2026-10-31 | Périmètre « * » de la matrice appliqué comme l'équipe de la personne et les équipes qu'elle dirige | Daouda KA | À valider par M. Sy | Hiérarchie du responsable commercial, produit et zone non appliqués : question 5 du cahier des charges |
| 21 | 2026-10-31 | La matrice de l'annexe G est chargée depuis un seul fichier (`matrice.py`) | Daouda KA | À valider par M. Sy | Le tableau est une proposition à relire par SYNESS ; un test vérifie le chargement, pas la justesse du tableau |
| 22 | 2026-10-31 | Journal d'audit branché sur l'administration (suppressions, modifications de droits), en lecture seule | Daouda KA | Décidé | Les exports et validations devront appeler `journaliser` quand leurs écrans existeront |
| 23 | 2026-10-31 | Hachage de mot de passe léger pendant les tests uniquement | Daouda KA | Décidé | Tests passés de 142 s à environ 40 s |
| 24 | 2026-10-31 | Police Lexend chargée depuis Google Fonts en développement | Daouda KA | À revoir avant la livraison | Héberger la police dans le projet : évite la dépendance externe et l'envoi de l'adresse IP des visiteurs à Google |


| 25 | Sur les fiches partenaires, seule la portée « toute » donne la liste ; le `L*` du dernier rôle (Lecteur autorisé) donne une liste vide. | Une fiche n'a ni propriétaire ni équipe, donc la portée restreinte ne peut pas s'appliquer. À préciser avec SYNESS. |
| 26 | Sur les fiches partenaires, créer ou modifier donne aussi le droit de consulter. | Le Responsable data a `CMVSE` sans `L` dans la matrice : sans cette règle, il ne verrait pas les fiches qu'il valide. À confirmer avec SYNESS. |



#	Décision	Raison
27	Détection des doublons : noms normalisés comparés par difflib, seuil de 0,85, pas d’alerte si les villes renseignées sont toutes différentes.	Règle simple et testable ; seuil à valider avec SYNESS.

28	Une alerte de doublon relie toujours la fiche la plus ancienne (A) à la plus récente (B).	La contrainte d’unicité porte sur la paire ordonnée.


#	Décision	Raison
29	Une vérification ajoute toujours une ligne d’historique. Conforme donne « Vérifié », à corriger remet « À vérifier », rejeté donne « Rejeté » ; le commentaire est obligatoire hors conformité.

33	L’import n’accepte que les sources aux conditions d’usage validées, contrôlé dans le formulaire et dans le service.	Règle du chapitre 4.7 : pas de collecte sans accord.
34	Une ligne invalide est comptée et listée avec son numéro, les autres sont importées.	Un seul défaut ne doit pas bloquer tout un fichier.
35	Chaque valeur importée garde sa provenance (source, collecte, champ, valeur, niveau « collecté »).	Traçabilité exigée par le cahier des charges.
36	Limites d’import : 1 000 lignes, 2 Mo, UTF-8 ; pays « Sénégal » par défaut.	Protège le serveur ; à valider avec SYNESS.
37	Les fiches importées passent par la détection des doublons ; réimporter un fichier crée donc des alertes.	Rien n’est rejeté en silence.


38	Réaffecter un prospect ajoute une ligne ReaffectationProspect (anciens et nouveaux commercial et équipe, auteur, motif, date) ; activités et tâches restent rattachées au prospect.	Critère du plan : un prospect réaffecté conserve tout son historique.
39	Seuls les droits de modification de portée « toute » ou « périmètre » permettent de réaffecter ; la portée « propre » (commercial) ne le permet pas.	Un commercial ne doit pas se défaire seul de ses prospects. À valider avec SYNESS.
40	La cible est un commercial actif de l’équipe de la personne qui réaffecte (toutes les équipes pour la portée « toute »).	Garde le prospect dans le périmètre de celui qui l’a déplacé.
41	Les tâches « à faire » suivent le nouveau commercial ; les tâches faites gardent leur responsable d’origine.	Les relances à venir sont à la charge du nouveau titulaire, le passé reste tracé.



42	Avertissement de contact multiple : un autre commercial suit un prospect actif (ni gagné, ni perdu, ni refusé) sur le même produit, avec le même partenaire ou un nom proche (similarité ≥ 0,85).	Évite que deux commerciaux démarchent le même client.
43	L’avertissement n’indique que le commercial, l’équipe, le statut et le motif, jamais le nom du prospect de l’autre équipe. Il ne bloque rien.	Respecte les droits de visibilité par équipe ; la décision de continuer reste au commercial.
44	La comparaison des noms se fait en Python sur les prospects actifs du même produit, sans index.	Suffisant pour la V1. À revoir si le volume dépasse quelques dizaines de milliers de prospects.


45	Activités et relances se saisissent depuis la fiche prospect. Le droit C (créer) et le droit M (modifier) de la ligne « Activités et relances » de la matrice s’appliquent avec leur portée : « propre » = seulement ses prospects.	Cohérent avec le reste des droits. À vérifier avec SYNESS : la matrice ne donne la saisie qu’au rôle « CML (p) ».
46	La première activité fait passer un prospect « Nouveau » à « Contacté ».	Garde le statut cohérent avec le travail réalisé, sans saisie en plus.
47	Une activité ne peut pas être datée dans le futur ; une échéance de tâche ne peut pas être dans le passé (tolérance de 5 minutes).	Une activité est un fait ; une tâche à faire est tournée vers l’avenir.
48	« Mes relances » liste les tâches à faire dont la personne est responsable, retards signalés. La vue d’équipe viendra avec les tableaux de bord (jalon 5).	Besoin immédiat d’un commercial ; la supervision a un autre usage.


49	Contrats : le commercial soumet (C, ses prospects) ; le Responsable commercial valide ou refuse (V) ; le chef d’équipe consulte seulement (L*).	Application directe de la ligne « Contrats » de la matrice. À valider avec SYNESS : le chef d’équipe ne valide pas.
50	Un refus exige un motif. valide_par enregistre la personne qui a décidé, en cas de validation comme de refus.	Un refus non expliqué est inutilisable pour le commercial.
51	Un contrat validé fait passer le prospect à « Gagné » ; un refus ne change pas son statut.	Le statut suit le résultat commercial réel.
52	Un seul contrat « soumis » ou « validé » par prospect ; après un refus, un nouveau contrat peut être soumis.	Évite les doublons de contrat sans bloquer la reprise après correction.
53	Un contrat décidé est définitif et on ne valide pas le contrat de ses propres prospects.	Traçabilité des décisions et séparation des rôles.
54	La date de signature d’un contrat ne peut pas être dans le futur.


56	Un objectif = produit + équipe + commercial optionnel + cible en contrats validés + période. Sans commercial, il est collectif.	Couvre les objectifs individuels et collectifs du plan avec un seul modèle.
57	La réalisation compte les contrats validés, signés pendant la période, sur le produit, pour les prospects actuellement suivis par le commercial (individuel) ou rattachés à l’équipe (collectif).	Indicateur simple et vérifiable. Limite connue : une réaffectation déplace le crédit vers le nouveau commercial. À valider avec SYNESS.
58	Le commercial d’un objectif doit appartenir à son équipe. Deux objectifs du même porteur (commercial ou équipe), sur le même produit, ne se chevauchent pas.	Évite les objectifs incohérents ou comptés deux fois.
59	Création et modification : Responsable commercial (portée « toute »). Consultation : selon la portée (équipe pour chef d’équipe, commercial et lecteur ; tout pour direction et analyste). La suppression (lettre S) n’est pas proposée.	Ligne « Campagnes et objectifs » de la matrice. On garde l’historique des objectifs.
60	Un seul indicateur de réalisation pour l’instant : les contrats validés.	Autres indicateurs (appels, rendez-vous) à définir avec SYNESS.



61	Le scénario de démonstration (Responsable commercial, contrats, objectifs, relances) est une commande à part, charger_scenario, qui s’appuie sur charger_demo sans la modifier.	Les tests supposent que les données de base sont vierges de contrats, d’objectifs et d’activités. Développement seulement.



#	Décision	Raison
62	Toute notification se crée par notifier(...). Une clé de regroupement évite de créer deux fois la même alerte pour la même personne (contrainte d’unicité en base).	Le plan demande de regrouper les alertes pour éviter les répétitions.
63	Le lien d’une notification doit être une adresse interne (commençant par /).	Empêche d’envoyer un utilisateur vers un site extérieur par une notification.
64	Chacun ne voit et ne modifie que ses propres notifications. Le marquage comme lu se fait en POST.	Confidentialité ; aucune modification par un simple lien.
65	La cloche (compteur de non lues) s’affiche dans toutes les pages pour un utilisateur connecté.	Informer chacun de ce qui relève de son rôle.


66	Les événements qui notifient sont regroupés dans notifications/evenements.py et appelés depuis les services de ventes, jamais depuis les vues : tous les chemins (écran, commande, import) notifient de la même façon.
67	L’auteur d’une action n’est jamais notifié de sa propre action. L’ancien commercial d’un prospect réaffecté est prévenu sans lien, car il n’a peut-être plus accès à la fiche.
68	Un contrat soumis alerte les personnes ayant le droit V sur les contrats (toute portée, ou périmètre si le prospect est dans leur équipe), sauf le commercial propriétaire. Le lien mène à « Contrats à valider » (cohérent avec la décision 55).
69	Les alertes de validation et de décision portent une clé de regroupement par contrat : un événement rejoué ne crée pas de doublon. Un refus est de priorité haute, une validation de priorité moyenne.
