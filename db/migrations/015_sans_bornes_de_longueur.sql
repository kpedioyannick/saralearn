-- =====================================================================
-- 015 — retrait des bornes de longueur sur `exercise`
--
-- Neuf colonnes de texte portaient une borne : l'énoncé à 240
-- caractères, le corps à 700, les titres à 80 et 160, les lignes de
-- retour à 200, l'explication à 600, l'astuce à 240. Elles venaient du
-- cahier des charges d'origine — « un écran, pas de scroll » — et
-- décrivaient une app où l'on répondait à des questions de grammaire de
-- cinquante caractères.
--
-- LE CATALOGUE A CHANGÉ AVANT LA CONTRAINTE. Les questions
-- d'informatique font déjà 100 caractères de médiane et montent à 240,
-- et le front a dû baisser la taille de police de 40 à 20 px pour les
-- encaisser (voir le commentaire dans `PhaseBlocks.tsx`). La borne ne
-- protégeait donc plus rien : elle avait déjà été contournée par la
-- mise en page. Avec un catalogue de culture générale, où l'explication
-- porte le fait lui-même, elle gênait franchement.
--
-- SQLITE NE SAIT PAS RETIRER UN CHECK. Il n'y a pas d'ALTER TABLE pour
-- ça : il faut bâtir la table voulue, y verser les lignes, échanger, et
-- refaire les index. C'est la manœuvre la plus risquée de ce dépôt —
-- `exercise` porte 3 185 lignes et trois tables pointent dessus
-- (`attempt`, `exercise_vote`, `exercise_comment`).
--
-- POURQUOI TOUTES LES BORNES D'UN COUP. La recréation est le coût, pas
-- le nombre de contraintes retirées. Ne lever que la borne de l'énoncé
-- obligerait à recommencer la même manœuvre le jour où l'explication
-- déborde — et à reprendre le même risque pour rien.
--
-- CE QUI EST CONSERVÉ, et qui n'a rien à voir avec la longueur :
--   · les types de question et de niveau admis
--   · `options` doit rester du JSON valide
--   · `correct_index >= 0`
--   · `state` parmi draft / validated / rejected
--   · toutes les clés étrangères, avec leurs ON DELETE
--   · les trois index
--
-- `foreign_keys` EST COUPÉ PENDANT L'ÉCHANGE et `migrate.py` passe un
-- `PRAGMA foreign_key_check` après coup : si une seule ligne d'`attempt`
-- se retrouvait orpheline, la base serait restaurée depuis la
-- sauvegarde. Le PRAGMA doit être posé HORS transaction, d'où sa place
-- avant le BEGIN.
--
--   python3 scripts/migrate.py db/migrations/015_sans_bornes_de_longueur.sql
-- =====================================================================

PRAGMA foreign_keys = OFF;

BEGIN;

-- ---------------------------------------------------------------------
-- La table voulue, sans une seule borne de longueur
-- ---------------------------------------------------------------------

CREATE TABLE exercise_neuf (
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

  -- Plus aucune borne ici : c'est tout l'objet de cette migration.
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
  exp_tip       TEXT,

  state         TEXT NOT NULL DEFAULT 'draft'
                CHECK (state IN ('draft','validated','rejected')),

  up_count      INTEGER NOT NULL DEFAULT 0,
  down_count    INTEGER NOT NULL DEFAULT 0,
  attempt_count INTEGER NOT NULL DEFAULT 0,

  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------
-- Le versement
--
-- Colonnes nommées une à une, jamais `SELECT *` : un ordre de colonnes
-- qui aurait glissé mettrait silencieusement `ko_line` dans `ok_line`.
-- ---------------------------------------------------------------------

INSERT INTO exercise_neuf (
  id, theme_id, exercise_prompt_id, sign_id,
  type_question, type_bloom, difficulty,
  prompt, body, options, correct_index,
  ok_title, ok_line, ko_title, ko_line,
  exp_title, exp_text, exp_tip,
  state, up_count, down_count, attempt_count,
  created_at, updated_at)
SELECT
  id, theme_id, exercise_prompt_id, sign_id,
  type_question, type_bloom, difficulty,
  prompt, body, options, correct_index,
  ok_title, ok_line, ko_title, ko_line,
  exp_title, exp_text, exp_tip,
  state, up_count, down_count, attempt_count,
  created_at, updated_at
FROM exercise;

-- ---------------------------------------------------------------------
-- Contrôle AVANT l'échange
--
-- `RAISE(ABORT, ...)` n'existe que dans un trigger. Pour échouer
-- volontairement au milieu d'un script, on viole une contrainte : cette
-- table temporaire n'accepte que la valeur 1. Le test est placé ICI,
-- avant le DROP : c'est tout l'intérêt. Si le compte ne tombe pas juste,
-- la transaction meurt alors que l'ancienne table est encore debout.
-- ---------------------------------------------------------------------

CREATE TEMP TABLE _controle_015 (
  test TEXT    NOT NULL,
  ok   INTEGER NOT NULL CHECK (ok = 1)
);

INSERT INTO _controle_015 (test, ok)
SELECT 'toutes les lignes ont été versées',
       (SELECT COUNT(*) FROM exercise_neuf) = (SELECT COUNT(*) FROM exercise);

-- Aucune valeur n'a glissé d'une colonne à l'autre : on recompte les
-- lignes dont chaque champ correspond exactement, jointes par leur id.
INSERT INTO _controle_015 (test, ok)
SELECT 'aucun champ n''a glissé de colonne',
       (SELECT COUNT(*) FROM exercise a JOIN exercise_neuf b USING (id)
         WHERE a.prompt IS b.prompt
           AND a.options IS b.options
           AND a.correct_index IS b.correct_index
           AND a.exp_text IS b.exp_text
           AND a.ok_line IS b.ok_line
           AND a.ko_line IS b.ko_line
           AND a.state IS b.state
           AND a.theme_id IS b.theme_id) = (SELECT COUNT(*) FROM exercise);

-- ---------------------------------------------------------------------
-- L'échange
--
-- DEUX VUES LISENT `exercise` et se cassent au DROP : SQLite refuse
-- alors le script entier avec « no such table: main.exercise », sans
-- dire laquelle est en cause. On les dépose ici et on les repose plus
-- bas, mot pour mot — leur définition n'est PAS modifiée par cette
-- migration, elle est seulement transportée.
--
-- Les deux autres vues (`v_global_rank`, `v_theme_week_rank`) ne lisent
-- qu'`attempt` et ne sont pas concernées.
-- ---------------------------------------------------------------------

DROP VIEW v_exercise_health;
DROP VIEW v_user_theme_progress;

DROP TABLE exercise;
ALTER TABLE exercise_neuf RENAME TO exercise;

-- Les index tombent avec la table : on les repose à l'identique.
CREATE INDEX ix_exercise_theme ON exercise (theme_id, state);
CREATE INDEX ix_exercise_state ON exercise (state, id);
CREATE INDEX ix_exercise_sign  ON exercise (sign_id);

-- Les deux vues, reposées telles qu'elles étaient.
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

-- ---------------------------------------------------------------------
-- Contrôle APRÈS l'échange
-- ---------------------------------------------------------------------

-- Les trois index sont revenus.
INSERT INTO _controle_015 (test, ok)
SELECT 'les trois index sont reposés',
       (SELECT COUNT(*) FROM sqlite_master WHERE type = 'index'
         AND tbl_name = 'exercise'
         AND name IN ('ix_exercise_theme','ix_exercise_state','ix_exercise_sign')) = 3;

-- Les quatre vues sont là, et les deux reposées répondent.
INSERT INTO _controle_015 (test, ok)
SELECT 'les quatre vues sont en place',
       (SELECT COUNT(*) FROM sqlite_master WHERE type = 'view') = 4;

INSERT INTO _controle_015 (test, ok)
SELECT 'les vues reposées interrogent bien la table',
       (SELECT COUNT(*) FROM v_exercise_health) = (SELECT COUNT(*) FROM exercise);

-- Plus aucune borne de longueur dans le schéma de la table.
INSERT INTO _controle_015 (test, ok)
SELECT 'plus aucune borne de longueur',
       (SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'exercise')
         NOT LIKE '%length(%';

-- Les tentatives n'ont perdu personne : elles pointent toutes sur un
-- exercice qui existe encore.
INSERT INTO _controle_015 (test, ok)
SELECT 'aucune tentative orpheline',
       NOT EXISTS (SELECT 1 FROM attempt a
                    LEFT JOIN exercise e ON e.id = a.exercise_id
                    WHERE e.id IS NULL);

COMMIT;

PRAGMA foreign_keys = ON;
