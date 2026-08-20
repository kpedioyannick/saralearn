-- =====================================================================
-- 018 — la fin des gabarits et du niveau de Bloom
--
-- Trois suppressions et un ajout, décidés après inventaire de ce qui
-- servait encore.
--
-- 1. LA TABLE `prompt` DISPARAÎT.
--
--    Elle ne contenait plus que deux coquilles, une par langue, créées
--    par `import_exercises.py` lui-même pour satisfaire le NOT NULL
--    d'`exercise_prompt.prompt_id`. Toutes deux `is_active = 0`,
--    `version = 999`, et un `template` qui se décrit comme jamais
--    envoyé : « Ce gabarit n'est jamais rendu ni envoyé à un modèle. »
--    Une table qui n'existait plus que pour se satisfaire elle-même.
--
--    `exercise_prompt.prompt_id` part avec elle, et le
--    CHECK (prompt_id IS NOT NULL OR chapter_id IS NOT NULL) aussi : il
--    exigeait une origine parmi deux, il n'en reste qu'une. On ne peut
--    pas rendre `chapter_id` obligatoire pour autant — les 202 lignes
--    existantes l'ont à NULL, et leur en inventer un serait un mensonge.
--
-- 2. LE NIVEAU DE BLOOM DISPARAÎT.
--
--    `exercise.type_bloom` valait `remember` sur 2 010 lignes sur
--    2 010 ; la migration 014 l'annonçait déjà : « une constante ».
--    `exercise_prompt.type_bloom`, ajouté par la 011 pour qu'un
--    lancement choisisse son niveau, est resté NULL sur 202 lignes sur
--    202 — le choix n'a jamais été fait une seule fois.
--
--    `difficulty` part dans le même mouvement. Elle n'a jamais été
--    saisie : elle était calculée depuis Bloom
--    (DIFFICULTY = {"remember": 1, ...}) et vaut donc 1 partout. Une
--    constante dérivée d'une constante. Si une notion de difficulté
--    revient un jour, elle viendra des taux de réussite réels — il n'y
--    a pas une seule ligne dans `attempt` à ce jour.
--
--    L'index ix_exercise_prompt_chapter_bloom tombe avec : il indexait
--    trois colonnes dont deux uniformément nulles.
--
-- 3. `exercise_prompt` GAGNE `parent_id`, VERS ELLE-MÊME.
--
--    Un lancement peut désormais en porter d'autres. Nullable, et il
--    doit le rester : les 202 lignes existantes n'ont pas de parent, et
--    la grande majorité des futures n'en aura pas non plus. ON DELETE
--    CASCADE — un parent qu'on efface emporte ses enfants, sans quoi on
--    laisserait des lots orphelins pointant dans le vide.
--
--    Le CHECK (parent_id <> id) coûte trois mots et interdit la boucle
--    la plus bête, celle d'une ligne qui se déclare sa propre mère.
--    SQLite ne sait pas interdire les cycles plus longs ; c'est au code
--    de ne pas en fabriquer.
--
-- CE QUI N'EST PAS TOUCHÉ
--
--    `exercise.type_question` reste, avec ses sept valeurs autorisées
--    pour un catalogue qui n'en emploie qu'une. La resserrer imposerait
--    une reconstruction de plus pour un gain nul.
--
--    Les quatre vues ne lisent ni `type_bloom`, ni `difficulty`, ni
--    `prompt`. Les deux qui lisent `exercise` sont malgré tout déposées
--    et reposées mot pour mot : SQLite refuse le DROP d'une table
--    qu'une vue référence, et se contente d'un « no such table » sans
--    dire laquelle. C'est la leçon de la 015.
--
--   python3 scripts/migrate.py db/migrations/018_sans_gabarit_ni_bloom.sql
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- Les vues d'abord : elles lisent `exercise` et bloqueraient son DROP.
-- Leur définition n'est PAS modifiée ici, seulement transportée.
-- ---------------------------------------------------------------------

DROP VIEW v_exercise_health;
DROP VIEW v_user_theme_progress;

-- ---------------------------------------------------------------------
-- `exercise` sans type_bloom ni difficulty
-- ---------------------------------------------------------------------

CREATE TABLE exercise_neuf (
  id                 INTEGER PRIMARY KEY,
  theme_id           INTEGER NOT NULL REFERENCES theme (id) ON DELETE CASCADE,
  exercise_prompt_id INTEGER          REFERENCES exercise_prompt (id) ON DELETE SET NULL,
  sign_id            INTEGER          REFERENCES sign (id) ON DELETE SET NULL,

  type_question TEXT NOT NULL
                CHECK (type_question IN ('qcm','true_false','complete','find_error',
                                         'reorder','short_answer','cloze')),

  -- Aucune borne de longueur : c'était l'objet de la 015.
  prompt        TEXT NOT NULL,
  body          TEXT,
  options       TEXT NOT NULL CHECK (json_valid(options)),
  correct_index INTEGER NOT NULL CHECK (correct_index >= 0),

  ok_title      TEXT,
  ok_line       TEXT,
  ko_title      TEXT,
  ko_line       TEXT,
  exp_title     TEXT,
  exp_text      TEXT NOT NULL,
  state         TEXT NOT NULL DEFAULT 'draft'
                CHECK (state IN ('draft','validated','rejected')),

  up_count      INTEGER NOT NULL DEFAULT 0,
  down_count    INTEGER NOT NULL DEFAULT 0,
  attempt_count INTEGER NOT NULL DEFAULT 0,

  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Colonnes nommées une à une, jamais `SELECT *` : un ordre qui aurait
-- glissé mettrait silencieusement `ko_line` dans `ok_line`.
INSERT INTO exercise_neuf (
  id, theme_id, exercise_prompt_id, sign_id,
  type_question,
  prompt, body, options, correct_index,
  ok_title, ok_line, ko_title, ko_line,
  exp_title, exp_text,
  state, up_count, down_count, attempt_count,
  created_at, updated_at)
SELECT
  id, theme_id, exercise_prompt_id, sign_id,
  type_question,
  prompt, body, options, correct_index,
  ok_title, ok_line, ko_title, ko_line,
  exp_title, exp_text,
  state, up_count, down_count, attempt_count,
  created_at, updated_at
FROM exercise;

-- ---------------------------------------------------------------------
-- `exercise_prompt` sans prompt_id ni type_bloom, avec parent_id
-- ---------------------------------------------------------------------

CREATE TABLE exercise_prompt_neuf (
  id              INTEGER PRIMARY KEY,
  theme_id        INTEGER NOT NULL REFERENCES theme (id) ON DELETE CASCADE,

  -- Un lancement peut en porter d'autres. Voir l'en-tête, point 3.
  parent_id       INTEGER          REFERENCES exercise_prompt_neuf (id) ON DELETE CASCADE,
  chapter_id      INTEGER          REFERENCES chapter (id) ON DELETE SET NULL,

  rendered_prompt TEXT    NOT NULL,
  model           TEXT,
  requested_count INTEGER NOT NULL DEFAULT 10,
  produced_count  INTEGER NOT NULL DEFAULT 0,

  status          TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','running','done','failed')),
  error           TEXT,

  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at     TEXT,

  CHECK (parent_id IS NULL OR parent_id <> id)
);

INSERT INTO exercise_prompt_neuf (
  id, theme_id, parent_id, chapter_id,
  rendered_prompt, model, requested_count, produced_count,
  status, error, created_at, finished_at)
SELECT
  id, theme_id, NULL, chapter_id,
  rendered_prompt, model, requested_count, produced_count,
  status, error, created_at, finished_at
FROM exercise_prompt;

-- ---------------------------------------------------------------------
-- Contrôle AVANT l'échange
--
-- `RAISE(ABORT, ...)` n'existe que dans un trigger. Pour échouer
-- volontairement au milieu d'un script, on viole une contrainte : cette
-- table n'accepte que la valeur 1. Le test est ICI, avant tout DROP —
-- si un compte ne tombe pas juste, la transaction meurt alors que les
-- anciennes tables sont encore debout.
-- ---------------------------------------------------------------------

CREATE TEMP TABLE _controle_018 (
  test TEXT    NOT NULL,
  ok   INTEGER NOT NULL CHECK (ok = 1)
);

INSERT INTO _controle_018 (test, ok)
SELECT 'les 2 010 exercices ont été versés',
       (SELECT COUNT(*) FROM exercise_neuf) = (SELECT COUNT(*) FROM exercise);

INSERT INTO _controle_018 (test, ok)
SELECT 'aucun champ d''exercice n''a glissé de colonne',
       (SELECT COUNT(*) FROM exercise a JOIN exercise_neuf b USING (id)
         WHERE a.prompt IS b.prompt
           AND a.options IS b.options
           AND a.correct_index IS b.correct_index
           AND a.exp_text IS b.exp_text
           AND a.ok_line IS b.ok_line
           AND a.ko_line IS b.ko_line
           AND a.state IS b.state
           AND a.theme_id IS b.theme_id
           AND a.exercise_prompt_id IS b.exercise_prompt_id)
       = (SELECT COUNT(*) FROM exercise);

INSERT INTO _controle_018 (test, ok)
SELECT 'les 202 lancements ont été versés',
       (SELECT COUNT(*) FROM exercise_prompt_neuf) = (SELECT COUNT(*) FROM exercise_prompt);

INSERT INTO _controle_018 (test, ok)
SELECT 'aucun champ de lancement n''a glissé de colonne',
       (SELECT COUNT(*) FROM exercise_prompt a JOIN exercise_prompt_neuf b USING (id)
         WHERE a.theme_id IS b.theme_id
           AND a.chapter_id IS b.chapter_id
           AND a.rendered_prompt IS b.rendered_prompt
           AND a.model IS b.model
           AND a.produced_count IS b.produced_count
           AND a.status IS b.status
           AND a.created_at IS b.created_at)
       = (SELECT COUNT(*) FROM exercise_prompt);

-- Chaque exercice retrouve son lancement : c'est le seul lien qui
-- survit à la double reconstruction, et le seul qu'on ne saurait pas
-- refaire s'il se perdait.
INSERT INTO _controle_018 (test, ok)
SELECT 'chaque exercice pointe toujours sur un lancement existant',
       (SELECT COUNT(*) FROM exercise_neuf e
         WHERE e.exercise_prompt_id IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM exercise_prompt_neuf p
                            WHERE p.id = e.exercise_prompt_id)) = 0;

-- ---------------------------------------------------------------------
-- L'échange
-- ---------------------------------------------------------------------

DROP TABLE exercise;
ALTER TABLE exercise_neuf RENAME TO exercise;

DROP TABLE exercise_prompt;
ALTER TABLE exercise_prompt_neuf RENAME TO exercise_prompt;

DROP TABLE prompt;

-- ---------------------------------------------------------------------
-- Les index tombent avec leurs tables : on repose ceux qui gardent un
-- sens. Disparaissent ix_exercise_prompt_prompt (sa colonne n'existe
-- plus) et ix_exercise_prompt_chapter_bloom (idem).
-- ---------------------------------------------------------------------

CREATE INDEX ix_exercise_theme ON exercise (theme_id, state);
CREATE INDEX ix_exercise_state ON exercise (state, id);
CREATE INDEX ix_exercise_sign  ON exercise (sign_id);

CREATE INDEX ix_exercise_prompt_theme   ON exercise_prompt (theme_id, status);
CREATE INDEX ix_exercise_prompt_chapter ON exercise_prompt (chapter_id);
-- Neuf : sans lui, lister les enfants d'un lancement balaie la table.
CREATE INDEX ix_exercise_prompt_parent  ON exercise_prompt (parent_id);

-- ---------------------------------------------------------------------
-- Les deux vues, reposées telles qu'elles étaient.
-- ---------------------------------------------------------------------

CREATE VIEW v_exercise_health AS
SELECT e.id AS exercise_id, e.theme_id, e.state, e.up_count, e.down_count,
       e.up_count + e.down_count AS votes,
       CASE WHEN e.up_count + e.down_count = 0 THEN NULL
            ELSE ROUND(100.0 * e.down_count / (e.up_count + e.down_count)) END AS down_pct,
       CASE WHEN e.up_count + e.down_count >= 5 AND e.down_count > e.up_count
            THEN 1 ELSE 0 END AS should_quarantine
FROM exercise e;

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

DROP TABLE _controle_018;

COMMIT;

PRAGMA integrity_check;
PRAGMA foreign_key_check;
