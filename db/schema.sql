-- =====================================================================
-- Sara — app d'exercices · schéma SQLite
--
-- ⚠ CE FICHIER NE REPRODUIT PLUS LA BASE. Il date du démarrage et n'a
-- pas suivi les 19 migrations. Il lui manque `chapter` et `sign`, il
-- déclare `exercise_like` là où la base a `exercise_vote`, et il garde
-- des bornes de longueur retirées par la 015. La vérité est dans
-- `data/sara.db` et dans `db/migrations/`. Ne pas s'en servir pour
-- recréer la base.
--
-- On part de zéro : pas de H5P, pas de reprise de sara_learn.
-- La source d'un thème est du Markdown, découpé en chapitres ; chaque
-- chapitre commande un lancement, et un lancement écrit ses exercices.
--
--   category ─┬─ sub_category ─┐
--             └────────────────┴─> theme ─< theme_tag >─ tag
--                                    │
--                                    └─< chapter ─< exercise_prompt >─┐
--                                                        │  ^─────────┘ (parent_id)
--                                                        └─< exercise
--
--   sqlite3 data/sara.db < db/schema.sql
--
-- Le portage MySQL vit dans db/schema.mysql.sql — même modèle, à
-- reprendre quand on quittera SQLite.
-- =====================================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;   -- lectures concurrentes pendant les écritures

-- ---------------------------------------------------------------------
-- Taxonomie
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS category (
  id         INTEGER PRIMARY KEY,
  slug       TEXT    NOT NULL UNIQUE,
  label      TEXT    NOT NULL,
  -- La maquette donne une couleur à chaque catégorie ; elle est héritée
  -- par les thèmes qui n'en définissent pas.
  color      TEXT    NOT NULL DEFAULT '#0A5C2C',
  position   INTEGER NOT NULL DEFAULT 0,
  created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sub_category (
  id          INTEGER PRIMARY KEY,
  category_id INTEGER NOT NULL REFERENCES category (id) ON DELETE CASCADE,
  slug        TEXT    NOT NULL,
  label       TEXT    NOT NULL,
  color       TEXT,
  position    INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
  UNIQUE (category_id, slug)
);

CREATE INDEX IF NOT EXISTS ix_sub_category_category ON sub_category (category_id);

CREATE TABLE IF NOT EXISTS tag (
  id    INTEGER PRIMARY KEY,
  slug  TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- Thème — l'unité à laquelle on s'abonne, et la source Markdown
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS theme (
  id              INTEGER PRIMARY KEY,
  -- category_id est dénormalisé : sub_category le porte déjà, mais un
  -- thème peut exister sans sous-catégorie et le flux de création
  -- demande les deux séparément.
  category_id     INTEGER NOT NULL REFERENCES category (id),
  sub_category_id INTEGER          REFERENCES sub_category (id) ON DELETE SET NULL,
  owner_id        INTEGER          REFERENCES app_user (id) ON DELETE SET NULL,

  slug            TEXT NOT NULL UNIQUE,
  title           TEXT NOT NULL,
  description     TEXT,
  color           TEXT,

  -- La source déposée par l'auteur. C'est elle qu'on donne au modèle.
  source_markdown TEXT,

  -- private : visible du seul auteur (défaut)
  -- pending : relecture demandée
  -- public  : visible de tous
  visibility      TEXT NOT NULL DEFAULT 'private'
                  CHECK (visibility IN ('private', 'pending', 'public')),

  exercise_count   INTEGER NOT NULL DEFAULT 0,
  subscriber_count INTEGER NOT NULL DEFAULT 0,

  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
  published_at TEXT
);

CREATE INDEX IF NOT EXISTS ix_theme_category     ON theme (category_id);
CREATE INDEX IF NOT EXISTS ix_theme_sub_category ON theme (sub_category_id);
CREATE INDEX IF NOT EXISTS ix_theme_owner        ON theme (owner_id);
-- Le feed ne tire que dans le public ; cet index porte la requête.
CREATE INDEX IF NOT EXISTS ix_theme_feed         ON theme (visibility, sub_category_id);

-- SQLite n'a pas d'ON UPDATE CURRENT_TIMESTAMP.
CREATE TRIGGER IF NOT EXISTS tg_theme_touch
AFTER UPDATE ON theme FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
  UPDATE theme SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TABLE IF NOT EXISTS theme_tag (
  theme_id INTEGER NOT NULL REFERENCES theme (id) ON DELETE CASCADE,
  tag_id   INTEGER NOT NULL REFERENCES tag (id)   ON DELETE CASCADE,
  PRIMARY KEY (theme_id, tag_id)
);

CREATE INDEX IF NOT EXISTS ix_theme_tag_tag ON theme_tag (tag_id);

-- ---------------------------------------------------------------------
-- Lancements — un texte envoyé au modèle, et ce qu'il en est sorti
-- ---------------------------------------------------------------------

-- Une exécution : ce thème, ce texte réellement envoyé, ce qui en est né.
-- Permet de remonter d'un exercice douteux au prompt exact qui l'a écrit.
-- `parent_id` pointe vers un autre lancement : une recharge de feed
-- rejoue la consigne d'un lancement antérieur et se déclare son enfant.
CREATE TABLE IF NOT EXISTS exercise_prompt (
  id              INTEGER PRIMARY KEY,
  -- L'unique rattachement, depuis la 019 : le thème se lit sur le
  -- chapitre. (`chapter` n'est pas déclarée dans ce fichier — voir
  -- l'avertissement en tête.)
  chapter_id      INTEGER NOT NULL REFERENCES chapter (id) ON DELETE CASCADE,
  parent_id       INTEGER          REFERENCES exercise_prompt (id) ON DELETE CASCADE,

  rendered_prompt TEXT    NOT NULL,
  model           TEXT,
  requested_count INTEGER NOT NULL DEFAULT 10,
  produced_count  INTEGER NOT NULL DEFAULT 0,

  status          TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','running','done','failed')),
  error           TEXT,

  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at     TEXT,

  -- Interdit la boucle la plus bête : une ligne sa propre mère. SQLite
  -- ne sait pas interdire les cycles plus longs, c'est au code de ne
  -- pas en fabriquer.
  CHECK (parent_id IS NULL OR parent_id <> id)
);

CREATE INDEX IF NOT EXISTS ix_exercise_prompt_chapter ON exercise_prompt (chapter_id, status);
CREATE INDEX IF NOT EXISTS ix_exercise_prompt_parent  ON exercise_prompt (parent_id);

-- ---------------------------------------------------------------------
-- Exercice — exactement les champs que l'écran consomme
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS exercise (
  id                 INTEGER PRIMARY KEY,
  theme_id           INTEGER NOT NULL REFERENCES theme (id) ON DELETE CASCADE,
  exercise_prompt_id INTEGER          REFERENCES exercise_prompt (id) ON DELETE SET NULL,

  -- Doit rester aligné sur `TypeQuestion` dans api/schemas.py : un type
  -- accepté ici mais absent là-bas fait tomber le feed entier en 500.
  --   short_answer  saisie libre ; `options` liste les graphies acceptées
  --   cloze         plusieurs trous ; chaque option porte `blank` et `correct`
  type_question TEXT NOT NULL
                CHECK (type_question IN ('qcm','true_false','complete','find_error',
                                         'reorder','short_answer','cloze')),

  -- Écran exercice. Limites de longueur imposées ici plutôt que dans
  -- l'UI : « un écran, pas de scroll » se tient à l'écriture.
  prompt        TEXT NOT NULL CHECK (length(prompt) <= 240),
  -- Production fautive à localiser — seulement sur find_error.
  body          TEXT          CHECK (body IS NULL OR length(body) <= 700),
  -- [{ "label": "…", "feedback": "…" }] — 2 à 4 entrées
  options       TEXT NOT NULL CHECK (json_valid(options)),
  -- Sans borne haute : pour `cloze`, la bonne réponse de chaque trou est
  -- marquée dans l'option elle-même et cette colonne ne veut rien dire.
  correct_index INTEGER NOT NULL CHECK (correct_index >= 0),

  -- Écrans félicitation / erreur / explication
  ok_title      TEXT CHECK (ok_title  IS NULL OR length(ok_title)  <= 80),
  ok_line       TEXT CHECK (ok_line   IS NULL OR length(ok_line)   <= 200),
  ko_title      TEXT CHECK (ko_title  IS NULL OR length(ko_title)  <= 80),
  ko_line       TEXT CHECK (ko_line   IS NULL OR length(ko_line)   <= 200),
  exp_title     TEXT CHECK (exp_title IS NULL OR length(exp_title) <= 160),
  exp_text      TEXT NOT NULL CHECK (length(exp_text) <= 600),

  -- draft     : sorti du modèle, pas encore relu
  -- validated : relu, servi dans le feed
  -- rejected  : écarté, conservé pour améliorer le prompt
  state         TEXT NOT NULL DEFAULT 'draft'
                CHECK (state IN ('draft','validated','rejected')),

  like_count    INTEGER NOT NULL DEFAULT 0,
  attempt_count INTEGER NOT NULL DEFAULT 0,

  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- L'index qui porte le feed : thème abonné + validé.
CREATE INDEX IF NOT EXISTS ix_exercise_feed       ON exercise (theme_id, state);
CREATE INDEX IF NOT EXISTS ix_exercise_prompt_run ON exercise (exercise_prompt_id);

CREATE TRIGGER IF NOT EXISTS tg_exercise_touch
AFTER UPDATE ON exercise FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
  UPDATE exercise SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- ---------------------------------------------------------------------
-- Utilisateur et activité
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS app_user (
  id            INTEGER PRIMARY KEY,
  -- L'app ouvre sur un exercice, sans compte : device_id identifie la
  -- session anonyme, l'email n'arrive que si le compte est créé.
  device_id     TEXT NOT NULL UNIQUE,
  email         TEXT UNIQUE,
  password_hash TEXT,
  display_name  TEXT,
  is_admin      INTEGER NOT NULL DEFAULT 0,
  muted         INTEGER NOT NULL DEFAULT 0,
  dark          INTEGER,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  last_seen_at  TEXT
);

-- Abonnements : ce que l'écran Paramètres coche et décoche.
CREATE TABLE IF NOT EXISTS user_theme (
  user_id    INTEGER NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
  theme_id   INTEGER NOT NULL REFERENCES theme (id)    ON DELETE CASCADE,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (user_id, theme_id)
);

CREATE INDEX IF NOT EXISTS ix_user_theme_theme ON user_theme (theme_id);

-- Compteurs et progression se dérivent d'ici. Pas de table de
-- compteurs : elle finit toujours par se désynchroniser.
CREATE TABLE IF NOT EXISTS attempt (
  id           INTEGER PRIMARY KEY,
  user_id      INTEGER NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
  exercise_id  INTEGER NOT NULL REFERENCES exercise (id) ON DELETE CASCADE,
  theme_id     INTEGER NOT NULL REFERENCES theme (id)    ON DELETE CASCADE,
  -- NULL = exercice passé au swipe sans répondre.
  chosen_index INTEGER,
  is_correct   INTEGER,
  answer_ms    INTEGER,
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Anti-répétition : les N derniers vus par cet utilisateur.
CREATE INDEX IF NOT EXISTS ix_attempt_recent   ON attempt (user_id, created_at);
-- Progression par thème.
CREATE INDEX IF NOT EXISTS ix_attempt_progress ON attempt (user_id, theme_id, is_correct);
-- Classement hebdomadaire d'un thème.
CREATE INDEX IF NOT EXISTS ix_attempt_rank     ON attempt (theme_id, created_at, user_id);
CREATE INDEX IF NOT EXISTS ix_attempt_exercise ON attempt (exercise_id);

CREATE TABLE IF NOT EXISTS exercise_like (
  user_id     INTEGER NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
  exercise_id INTEGER NOT NULL REFERENCES exercise (id) ON DELETE CASCADE,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (user_id, exercise_id)
);

CREATE INDEX IF NOT EXISTS ix_exercise_like_exercise ON exercise_like (exercise_id);

-- Le cahier des charges dit « champ libre, envoyé à l'admin ».
CREATE TABLE IF NOT EXISTS exercise_comment (
  id          INTEGER PRIMARY KEY,
  user_id     INTEGER NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
  exercise_id INTEGER NOT NULL REFERENCES exercise (id) ON DELETE CASCADE,
  body        TEXT NOT NULL CHECK (length(body) <= 1000),
  is_read     INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS ix_exercise_comment_exercise ON exercise_comment (exercise_id, created_at);
CREATE INDEX IF NOT EXISTS ix_exercise_comment_unread   ON exercise_comment (is_read, created_at);

-- ---------------------------------------------------------------------
-- Classement — barème en un seul endroit
--
-- Une bonne réponse vaut 10, une tentative vaut 2, un exercice passé au
-- swipe ne rapporte rien. Le classement d'un thème repart chaque lundi :
-- strftime('%w') rend 0 pour dimanche, d'où le +6 %7 pour caler sur lundi.
-- ---------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS v_theme_week_rank AS
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

-- Classement global, toutes périodes — l'onglet « Les autres ».
CREATE VIEW IF NOT EXISTS v_global_rank AS
SELECT
  a.user_id,
  SUM(CASE WHEN a.is_correct = 1 THEN 10
           WHEN a.is_correct = 0 THEN 2
           ELSE 0 END)                   AS points,
  SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS passed,
  COUNT(*)                               AS attempts
FROM attempt a
GROUP BY a.user_id;

-- Les pourcentages ne vivent que là.
CREATE VIEW IF NOT EXISTS v_user_theme_progress AS
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
