-- =====================================================================
-- 010 — une catégorie « Computing », côté anglais
--
-- Git, les méthodes agiles et SQL entrent au catalogue. Ils y entrent
-- SOUS UNE SEULE CATÉGORIE, décidée ici et non par le modèle.
--
-- C'est le point que `api/outline.py` réclame en toutes lettres : le
-- modèle reçoit les catégories existantes et doit en désigner une. Sans
-- catégorie d'accueil, il en inventerait une par sujet — « Version
-- control », « Agile methods », « Databases » — et douze connaissances
-- feraient trois catégories pour deux thèmes chacune. Une taxonomie qui
-- se dédouble ne se recolle pas : les thèmes y pendent déjà.
--
-- Une seule, et large. « Computing » accueillera aussi bien un sujet sur
-- Docker ou les tests que ceux d'aujourd'hui ; Git, Agile et SQL se
-- distinguent par leurs TAGS, qui eux se corrigent en une requête.
--
-- `label` reste le libellé français et `label_en` l'anglais, comme pour
-- `grammar-en` et `spelling-en` : `api/routers/taxonomy.py` choisit
-- entre les deux selon la langue du lecteur, et un `label_en` vide
-- afficherait le mot français à un anglophone.
--
-- Position 3 : après Grammar (1) et Spelling (2), les deux seules
-- catégories anglaises. Rien ne bouge côté français.
--
-- La couleur ne reprend pas le bleu des catégories anglaises. Ces deux-là
-- enseignent une langue et forment une famille ; celle-ci n'en est pas,
-- et le catalogue les distingue à la pastille avant de les lire.
--
--   python3 scripts/migrate.py db/migrations/010_categorie_informatique_en.sql
-- =====================================================================

BEGIN;

INSERT INTO category (slug, label, label_en, lang, color, position, status)
VALUES ('computing-en', 'Informatique', 'Computing', 'en', '#0F766E', 3, 'active');

COMMIT;

PRAGMA integrity_check;
PRAGMA foreign_key_check;
