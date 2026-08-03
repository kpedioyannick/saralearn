-- =====================================================================
-- 007 — deux types de questions du catalogue des designers
--
-- Jusqu'ici les trois types servis — qcm, complete, find_error —
-- demandaient tous le même geste : taper un bouton parmi quatre. C'est
-- de la RECONNAISSANCE. Reconnaître « allées » parmi quatre formes n'est
-- pas savoir l'écrire.
--
-- On ouvre deux types qui demandent de PRODUIRE :
--
--   short_answer  Un champ de saisie. Les graphies acceptées sont
--                 listées dans `options` ; la comparaison se fait après
--                 normalisation (casse, accents, ponctuation).
--                 `correct_index` vaut 0 par convention.
--
--   cloze         Plusieurs trous dans un même texte, CHACUN avec ses
--                 propres candidats — jamais une banque commune, sinon
--                 l'élève élimine par recoupement au lieu de savoir.
--                 Chaque entrée de `options` porte `blank` (l'indice du
--                 trou) et `correct` (booléen). `correct_index` reste à
--                 0 : il ne veut rien dire pour ce type, mais la colonne
--                 est NOT NULL.
--
-- Trois contraintes CHECK doivent bouger, et SQLite ne sait pas les
-- modifier en place : il faut reconstruire la table.
--   · type_question — deux valeurs de plus
--   · body          — 400 → 700 caractères, un texte à trous est long
--   · correct_index — la borne haute 3 devient inutile pour cloze
--
-- RECONSTRUCTION — l'ordre compte, et une erreur ici efface la table.
-- On désactive les clés étrangères le temps de l'échange (sinon les
-- lignes filles seraient supprimées en cascade), on vérifie le nombre de
-- lignes AVANT de supprimer l'ancienne, et le tout dans une transaction.
--
--   python3 scripts/migrate.py db/migrations/007_saisie_libre_et_trous.sql
-- =====================================================================

PRAGMA foreign_keys = OFF;

BEGIN;

-- Les quatre vues lisent `exercise`. Au moment du RENAME, SQLite
-- reparse tout le schéma et bute sur des vues qui pointent vers une
-- table disparue. On les retire d'abord, on les recrée à l'identique
-- ensuite — leur définition est reprise telle quelle de la base.
DROP VIEW IF EXISTS v_exercise_health;
DROP VIEW IF EXISTS v_global_rank;
DROP VIEW IF EXISTS v_theme_week_rank;
DROP VIEW IF EXISTS v_user_theme_progress;

CREATE TABLE exercise_new (
  id                 INTEGER PRIMARY KEY,
  theme_id           INTEGER NOT NULL REFERENCES theme (id) ON DELETE CASCADE,
  exercise_prompt_id INTEGER          REFERENCES exercise_prompt (id) ON DELETE SET NULL,
  sign_id            INTEGER          REFERENCES sign (id) ON DELETE SET NULL,

  type_question TEXT NOT NULL
                CHECK (type_question IN ('qcm','true_false','complete','find_error',
                                         'reorder','short_answer','cloze')),
  type_bloom    TEXT NOT NULL
                CHECK (type_bloom IN ('remember','understand','apply','analyze')),
  difficulty    INTEGER NOT NULL DEFAULT 2,

  prompt        TEXT NOT NULL CHECK (length(prompt) <= 240),
  -- 700 : un texte à trous porte la phrase entière, pas un fragment.
  body          TEXT          CHECK (body IS NULL OR length(body) <= 700),
  options       TEXT NOT NULL CHECK (json_valid(options)),
  -- La borne haute tombe : pour `cloze`, la bonne réponse de chaque trou
  -- est marquée dans l'option elle-même, et cette colonne ne sert plus.
  correct_index INTEGER NOT NULL CHECK (correct_index >= 0),

  ok_title      TEXT CHECK (ok_title  IS NULL OR length(ok_title)  <= 80),
  ok_line       TEXT CHECK (ok_line   IS NULL OR length(ok_line)   <= 200),
  ko_title      TEXT CHECK (ko_title  IS NULL OR length(ko_title)  <= 80),
  ko_line       TEXT CHECK (ko_line   IS NULL OR length(ko_line)   <= 200),
  exp_title     TEXT CHECK (exp_title IS NULL OR length(exp_title) <= 160),
  exp_text      TEXT NOT NULL CHECK (length(exp_text) <= 600),
  exp_tip       TEXT CHECK (exp_tip   IS NULL OR length(exp_tip)   <= 240),

  state         TEXT NOT NULL DEFAULT 'draft'
                CHECK (state IN ('draft','validated','rejected')),

  up_count      INTEGER NOT NULL DEFAULT 0,
  down_count    INTEGER NOT NULL DEFAULT 0,
  attempt_count INTEGER NOT NULL DEFAULT 0,

  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO exercise_new
  (id, theme_id, exercise_prompt_id, sign_id, type_question, type_bloom,
   difficulty, prompt, body, options, correct_index, ok_title, ok_line,
   ko_title, ko_line, exp_title, exp_text, exp_tip, state,
   up_count, down_count, attempt_count, created_at, updated_at)
SELECT
   id, theme_id, exercise_prompt_id, sign_id, type_question, type_bloom,
   difficulty, prompt, body, options, correct_index, ok_title, ok_line,
   ko_title, ko_line, exp_title, exp_text, exp_tip, state,
   up_count, down_count, attempt_count, created_at, updated_at
FROM exercise;

-- Garde-fou : la copie doit être complète avant qu'on supprime quoi que
-- ce soit. `RAISE` n'existe que dans un trigger, et le CLI sqlite3
-- POURSUIT après une erreur — un contrôle mal écrit ici ne protège de
-- rien et laisse le DROP s'exécuter quand même. On le pose donc sur une
-- contrainte que SQLite fait respecter lui-même : la requête échoue, et
-- comme on est dans une transaction, le COMMIT final n'aura pas lieu.
--
-- Ce fichier doit être joué par `scripts/migrate.py`, qui s'arrête à la
-- première erreur. Le jouer avec `sqlite3 < fichier` détruirait la table.
CREATE TABLE migration_guard_007 (ok INTEGER NOT NULL CHECK (ok = 1));
INSERT INTO migration_guard_007 (ok)
SELECT (SELECT COUNT(*) FROM exercise_new) = (SELECT COUNT(*) FROM exercise);

DROP TABLE exercise;
ALTER TABLE exercise_new RENAME TO exercise;

CREATE INDEX IF NOT EXISTS ix_exercise_theme ON exercise (theme_id, state);
CREATE INDEX IF NOT EXISTS ix_exercise_state ON exercise (state, id);
CREATE INDEX IF NOT EXISTS ix_exercise_sign  ON exercise (sign_id);

CREATE VIEW v_exercise_health AS
SELECT e.id AS exercise_id, e.theme_id, e.state, e.up_count, e.down_count,
       e.up_count + e.down_count AS votes,
       CASE WHEN e.up_count + e.down_count = 0 THEN NULL
            ELSE ROUND(100.0 * e.down_count / (e.up_count + e.down_count)) END AS down_pct,
       CASE WHEN e.up_count + e.down_count >= 5 AND e.down_count > e.up_count
            THEN 1 ELSE 0 END AS should_quarantine
FROM exercise e;

CREATE VIEW v_global_rank AS
SELECT
  a.user_id,
  SUM(CASE WHEN a.is_correct = 1 THEN 10
           WHEN a.is_correct = 0 THEN 2
           ELSE 0 END)                   AS points,
  SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS passed,
  COUNT(*)                               AS attempts
FROM attempt a
GROUP BY a.user_id;

CREATE VIEW v_theme_week_rank AS
SELECT
  a.theme_id,
  a.user_id,
  date(a.created_at, '-' || ((CAST(strftime('%w', a.created_at) AS INTEGER) + 6) % 7) || ' days')
    AS week_start,
  SUM(CASE WHEN a.is_correct = 1 THEN 10
           WHEN a.is_correct = 0 THEN 2
           ELSE 0 END)                          AS points,
  SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END)        AS passed,
  SUM(CASE WHEN a.chosen_index IS NOT NULL THEN 1 ELSE 0 END) AS answered
FROM attempt a
GROUP BY a.theme_id, a.user_id, week_start;

CREATE VIEW v_user_theme_progress AS
SELECT
  a.user_id,
  a.theme_id,
  COUNT(DISTINCT CASE WHEN a.is_correct = 1 THEN a.exercise_id END) AS passed,
  (SELECT COUNT(*) FROM exercise e
     WHERE e.theme_id = a.theme_id AND e.state = 'validated')       AS total,
  CAST(ROUND(
    100.0 * COUNT(DISTINCT CASE WHEN a.is_correct = 1 THEN a.exercise_id END)
    / NULLIF((SELECT COUNT(*) FROM exercise e
                WHERE e.theme_id = a.theme_id AND e.state = 'validated'), 0)
  ) AS INTEGER)                                                     AS pct
FROM attempt a
GROUP BY a.user_id, a.theme_id;

DROP TABLE migration_guard_007;

COMMIT;

PRAGMA foreign_keys = ON;
PRAGMA foreign_key_check;
