-- =====================================================================
-- 012 — les titres de repli des exercices anglais
--
-- `llm.validate` pose un titre quand le modèle a omis le sien :
-- « Bien vu. » sur une bonne réponse, « Presque. » sur une mauvaise.
-- Ces deux textes étaient écrits en dur, en français, et sont AFFICHÉS
-- À L'ÉLÈVE — un « Presque. » sous une question sur `git merge` se
-- remarque au premier coup d'œil.
--
-- Le code est corrigé (`FALLBACK_TITLES`, suivi de la langue du thème).
-- Restent les lignes déjà écrites : 9 « Bien vu. » et 20 « Presque. »
-- sur les 1532 exercices anglais, soit les cas où le modèle avait sauté
-- le titre.
--
-- On ne touche QUE les thèmes en anglais, et QUE ces deux valeurs
-- exactes. Un « Presque. » écrit par le modèle dans un thème français
-- est légitime et doit rester.
--
--   python3 scripts/migrate.py db/migrations/012_titres_de_repli_anglais.sql
-- =====================================================================

BEGIN;

UPDATE exercise
   SET ok_title = 'Nice one.'
 WHERE ok_title = 'Bien vu.'
   AND theme_id IN (SELECT id FROM theme WHERE lang = 'en');

UPDATE exercise
   SET ko_title = 'Not quite.'
 WHERE ko_title = 'Presque.'
   AND theme_id IN (SELECT id FROM theme WHERE lang = 'en');

COMMIT;

PRAGMA integrity_check;
