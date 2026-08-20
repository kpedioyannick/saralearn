-- =====================================================================
-- 013 — retrait de la sous-catégorie
--
-- `sub_category` portait un deuxième niveau sous une catégorie. Une
-- seule ligne a jamais été créée — « Auto » sous « Permis de conduire »,
-- pour découper le permis par véhicule — et le deuxième niveau n'est
-- jamais venu.
--
-- Surtout, l'écran de création ne l'a JAMAIS proposée : `draftSubCategoryId`
-- naît à `null` dans le store du front et rien ne l'écrit entre sa
-- déclaration et son envoi à l'API. Tout thème créé depuis l'app naît
-- donc sans sous-catégorie, par construction — 93 des 106 thèmes.
--
-- Des 13 thèmes rattachés, 2 sont légitimes (`panneaux-france` et
-- `road-signs-usa`, des panneaux routiers sous le permis) et 11 sont
-- les restes d'une campagne de test du 3 août : onze « Harmonie à la
-- guitare » à zéro exercice, classées sous le permis de conduire parce
-- que le formulaire de test portait la catégorie en dur.
--
-- CE QUI CHANGE POUR L'ÉLÈVE : les deux thèmes de panneaux perdent la
-- mention « · Auto » sous leur titre. Ils restent sous « Permis de
-- conduire », et leurs 439 exercices ne bougent pas.
--
-- LES 11 THÈMES DE TEST NE SONT PAS SUPPRIMÉS ICI. Effacer une table de
-- taxonomie et effacer du contenu sont deux décisions distinctes ; la
-- seconde n'a pas été demandée, et elle se prendra en la regardant en
-- face. Leur origine est `tests/test_api.py`, qui crée « Harmonie à la
-- guitare » à chaque passage sans jamais la reprendre.
--
-- `db/schema.sql` N'EST PAS MODIFIÉ : c'est le schéma d'ORIGINE, pas le
-- schéma courant — il ignore déjà `lang` et `label_en`, posés par les
-- migrations 002 et 005. Une base neuve se bâtit en le jouant PUIS en
-- appliquant les migrations dans l'ordre, celle-ci comprise.
--
--   python3 scripts/migrate.py db/migrations/013_retrait_de_la_sous_categorie.sql
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- Le garde-fou.
--
-- Il tient sur une contrainte que SQLite fait respecter LUI-MÊME. Un
-- `RAISE(ABORT, …)` n'existe qu'à l'intérieur d'un trigger : posé ici,
-- il ne s'exécuterait pas, et un garde-fou qui ne s'exécute pas est
-- pire que pas de garde-fou.
--
-- Ce qu'il compte : les sous-catégories RÉELLEMENT UTILISÉES, c'est-à-
-- dire celles auxquelles au moins un thème est rattaché. Compter les
-- lignes de `sub_category` serait le mauvais repère — la migration 005
-- en sème cinq qui n'ont jamais servi, et une base reconstruite depuis
-- `db/schema.sql` puis toutes les migrations bloquerait ici sans raison.
--
-- Une seule sous-catégorie porte des thèmes en production (« Auto »).
-- Si quelqu'un en a bâti et peuplé plusieurs entre-temps, l'INSERT
-- viole le CHECK, `executescript` lève, et `scripts/migrate.py` restaure
-- la base depuis sa sauvegarde.
-- ---------------------------------------------------------------------
CREATE TABLE _garde_sous_categorie (n INTEGER NOT NULL CHECK (n <= 1));
INSERT INTO _garde_sous_categorie
  SELECT COUNT(DISTINCT sub_category_id) FROM theme WHERE sub_category_id IS NOT NULL;
DROP TABLE _garde_sous_categorie;

-- ---------------------------------------------------------------------
-- Les index d'abord : SQLite refuse de retirer une colonne indexée.
--
-- `ix_theme_feed` était sur (visibility, sub_category_id). On le
-- recrée sur sa seule première colonne : toute requête qui s'appuyait
-- sur le préfixe `visibility` continue d'être servie à l'identique.
-- ---------------------------------------------------------------------
DROP INDEX IF EXISTS ix_theme_sub_category;
DROP INDEX IF EXISTS ix_theme_feed;

ALTER TABLE theme DROP COLUMN sub_category_id;

CREATE INDEX ix_theme_feed ON theme (visibility);

-- La table en dernier : tant que `theme.sub_category_id` existe, la
-- supprimer laisserait une clé étrangère pendante.
DROP INDEX IF EXISTS ix_sub_category_lang;
DROP INDEX IF EXISTS ix_sub_category_category;
DROP TABLE sub_category;

COMMIT;

PRAGMA integrity_check;
PRAGMA foreign_key_check;
