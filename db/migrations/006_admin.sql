-- =====================================================================
-- 006 — administration
--
-- AUCUN changement de forme. `app_user.is_admin` existe depuis le
-- premier schéma (db/schema.sql), et `themes.py` s'en sert déjà pour
-- laisser un administrateur éditer le thème d'un autre. On ne rajoute
-- ni colonne ni table pour l'écran d'admin : le mécanisme est là.
--
-- Ce qui manque n'est pas une colonne, c'est un administrateur —
-- `SELECT COUNT(*) FROM app_user WHERE is_admin = 1` renvoie 0. D'où
-- ce fichier : un index pour la file de relecture, et le geste de
-- promotion, à faire une fois.
--
--   sqlite3 data/sara.db < db/migrations/006_admin.sql
-- =====================================================================

PRAGMA foreign_keys = ON;

-- La file de relecture lit `WHERE visibility = 'pending' ORDER BY
-- published_at`. `ix_theme_feed` porte bien `visibility`, mais suivi de
-- `sub_category_id` : il filtre, il ne trie pas. Celui-ci rend la file
-- ordonnée sans passage de tri.
CREATE INDEX IF NOT EXISTS ix_theme_review ON theme (visibility, published_at);

-- ---------------------------------------------------------------------
-- Le premier administrateur
--
-- À faire une fois, avec un compte qui a un email — un compte anonyme
-- n'a pas de moyen de se reconnecter, en faire un admin serait donner
-- les clés à un appareil, pas à quelqu'un. Décommente et remplace :
--
--   UPDATE app_user SET is_admin = 1 WHERE email = 'a-toi@example.com';
--
-- Vérification :
--
--   SELECT id, email, display_name FROM app_user WHERE is_admin = 1;
--
-- Tant que cette ligne n'est pas jouée, l'écran #admin ne s'ouvre que
-- par le jeton de service : `SARA_ADMIN_TOKEN` dans l'environnement de
-- sara-exos-api.service, collé dans le champ de l'écran. C'est une
-- porte d'amorçage, pas un mode de fonctionnement — le jeton n'identifie
-- personne, donc aucun geste d'admin n'est attribuable tant qu'on passe
-- par lui.
-- ---------------------------------------------------------------------
