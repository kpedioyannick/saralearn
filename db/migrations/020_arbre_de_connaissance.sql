-- =====================================================================
-- 020 — le modèle en quatre niveaux, et l'arbre de connaissance
--
-- Le vocabulaire ne correspondait plus à ce que le projet enseigne. Une
-- « catégorie » était en fait un domaine du monde créé, un « thème » un
-- sujet, un « chapitre » une tranche de ce sujet. Les mots sont remis
-- sur les choses :
--
--     category  →  theme              La lumière, Le ciel, La terre…
--     theme     →  chapter            un sujet, ancré sur un article
--     chapter   →  exercise_prompt    une section de cet article
--     exercise  →  exercise           inchangé
--
-- LE MOMENT EST CHOISI. Les quatre tables ont été vidées avant cette
-- migration — 1 960 exercices, 202 lancements, 196 chapitres et 36
-- thèmes, tous sauvegardés dans data/sara.db.avant-remise-a-zero-*. Il
-- ne reste que les 6 catégories. Une rotation de noms sur des tables
-- pleines aurait été un exercice d'équilibriste ; sur des tables vides,
-- c'est une réécriture.
--
-- NEUF THÈMES, PAS SIX
--
--   Deux catégories se scindent : « The Earth, the Sea and Vegetation »
--   donne The Earth et Vegetation, « The Sun, the Moon and the Stars »
--   donne The Sun, The Moon et The Stars. Ce n'est pas cosmétique : un
--   thème doit avoir UN article-graine évident, et le groupe des trois
--   astres n'en avait aucun — il fallait remonter à
--   `Astronomical_object`, signe que le regroupement était faux.
--
-- L'ARBRE
--
--   `chapter.parent_id` pointe vers un autre chapitre. Une racine par
--   thème, et rien qu'une : l'index partiel ux_chapter_root n'indexe
--   que les lignes sans parent, donc il en interdit une seconde. La
--   contrainte est posée en base, elle ne se surveille pas à la main.
--
--   `chapter.source_url` est UNIQUE, et c'est la condition d'arrêt du
--   crawl : la boucle tente l'insertion, se prend un conflit, et sait
--   qu'elle revient sur du déjà-vu. Pas de liste à tenir à côté.
--
-- DEUX ARBRES, PAS UN
--
--   `chapter` porte l'arbre des SUJETS, tiré des renvois « Main article »
--   d'un article vers l'article dédié d'un sous-sujet. Mesuré : depuis
--   `Sky`, 5 sous-sujets au niveau 1, puis 31, puis 198, puis 8 — et au
--   niveau 4, quatre articles sur cinq n'ont plus aucun sous-sujet.
--   L'arbre s'épuise de lui-même, contrairement aux liens du corps de
--   l'article, qui donnent 8 462 candidats dès le niveau 1 et n'en
--   finissent jamais.
--
--   `exercise_prompt` porte l'arbre des SECTIONS d'un même article. Une
--   section sans sous-section garde son contenu ; une section qui en a
--   n'est qu'un titre, et ses sous-sections deviennent ses enfants. Le
--   contenu est donc toujours sur une feuille, et c'est une feuille qui
--   produit des exercices.
--
-- L'ANGLAIS SEUL
--
--   `category.label` (français) et `label_en` fusionnent en un `title`.
--   La colonne `lang` disparaît : elle valait 'en' partout. Le français
--   ne revient qu'au prix d'une migration, et c'est très bien ainsi —
--   la moitié des redondances de ce schéma venaient de là.
--
-- CE QUI EST SUPPRIMÉ SANS RETOUR
--
--   `tag` et `theme_tag`, vides depuis toujours et jamais lues par une
--   seule ligne de code.
--
--   python3 scripts/migrate.py db/migrations/020_arbre_de_connaissance.sql
-- =====================================================================

BEGIN;

-- Les vues lisent `exercise` et `attempt` : elles bloqueraient les DROP.
-- Reposées en fin de migration, adaptées au nouveau vocabulaire.
DROP VIEW IF EXISTS v_exercise_health;
DROP VIEW IF EXISTS v_user_theme_progress;
DROP VIEW IF EXISTS v_global_rank;
DROP VIEW IF EXISTS v_theme_week_rank;

-- Garde-fou : cette migration écrase des tables. Si l'une n'était pas
-- vide, on s'arrêterait ici plutôt que de détruire du contenu.
CREATE TEMP TABLE _controle_020 (
  test TEXT    NOT NULL,
  ok   INTEGER NOT NULL CHECK (ok = 1)
);
INSERT INTO _controle_020 (test, ok)
SELECT 'les tables à réécrire sont bien vides',
       (SELECT COUNT(*) FROM exercise)
     + (SELECT COUNT(*) FROM exercise_prompt)
     + (SELECT COUNT(*) FROM chapter)
     + (SELECT COUNT(*) FROM theme)
     + (SELECT COUNT(*) FROM attempt) = 0;

-- ---------------------------------------------------------------------
-- theme — les neuf domaines du monde créé
-- ---------------------------------------------------------------------

CREATE TABLE theme_neuf (
  id          INTEGER PRIMARY KEY,
  slug        TEXT    NOT NULL UNIQUE,
  title       TEXT    NOT NULL,
  description TEXT,

  -- L'article d'où part le crawl. Un seul par thème : c'est la racine
  -- de l'arbre, et le premier chapitre que le script créera.
  seed_url    TEXT,

  color       TEXT    NOT NULL DEFAULT '#0A5C2C',
  position    INTEGER NOT NULL DEFAULT 0,
  status      TEXT    NOT NULL DEFAULT 'active'
              CHECK (status IN ('draft','active')),
  created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO theme_neuf (slug, title, description, seed_url, color, position) VALUES
  ('light',           'Light',
   'What light is, how it travels, and everything that shines or casts a shadow.',
   'https://en.wikipedia.org/wiki/Light',      '#CA8A04', 1),
  ('the-sky',         'The Sky',
   'The air above us, the water it carries, and the weather it makes.',
   'https://en.wikipedia.org/wiki/Sky',        '#0284C7', 2),
  ('the-earth',       'The Earth',
   'The ground under our feet, the seas that cover it, and the shapes it takes.',
   'https://en.wikipedia.org/wiki/Earth',      '#92400E', 3),
  ('vegetation',      'Vegetation',
   'Everything that grows rooted — from moss on a stone to the tallest tree.',
   'https://en.wikipedia.org/wiki/Plant',      '#15803D', 4),
  ('the-sun',         'The Sun',
   'The star we live beside: its light, its heat, and the year it rules.',
   'https://en.wikipedia.org/wiki/Sun',        '#EA580C', 5),
  ('the-moon',        'The Moon',
   'Why it changes shape, why one side is never seen, and how it pulls the sea.',
   'https://en.wikipedia.org/wiki/Moon',       '#64748B', 6),
  ('the-stars',       'The Stars',
   'What a star is, what travels with them, and how far the night sky reaches.',
   'https://en.wikipedia.org/wiki/Star',       '#4338CA', 7),
  ('the-animals',     'The Animals',
   'How animals move, feed, defend themselves and raise their young.',
   'https://en.wikipedia.org/wiki/Animal',     '#BE123C', 8),
  ('the-human-being', 'The Human Being',
   'The body, its senses, and everything it does without being told to.',
   'https://en.wikipedia.org/wiki/Human_body', '#9333EA', 9);

-- ---------------------------------------------------------------------
-- chapter — un sujet, ancré sur un article, et l'arbre qui les relie
-- ---------------------------------------------------------------------

CREATE TABLE chapter_neuf (
  id          INTEGER PRIMARY KEY,
  theme_id    INTEGER NOT NULL REFERENCES theme_neuf (id) ON DELETE CASCADE,

  -- NULL = racine du thème. L'index partiel plus bas en interdit deux.
  parent_id   INTEGER          REFERENCES chapter_neuf (id) ON DELETE CASCADE,
  -- Redondant avec la remontée des parents, mais un crawl borné en
  -- profondeur doit pouvoir filtrer sans récursion à chaque candidat.
  depth       INTEGER NOT NULL DEFAULT 0,
  position    INTEGER NOT NULL DEFAULT 0,

  slug        TEXT    NOT NULL UNIQUE,
  title       TEXT    NOT NULL,
  description TEXT,

  -- UNIQUE : c'est la condition d'arrêt du crawl. Voir l'en-tête.
  source_url  TEXT    UNIQUE,
  -- {"wikipedia": "…", "pageid": 123, "revision": 456,
  --  "related": ["…"], "fetched_at": "…"}
  meta        TEXT    CHECK (meta IS NULL OR json_valid(meta)),

  -- draft     : posé par le crawl, pas encore relu
  -- validated : retenu, prêt à produire des exercices
  -- rejected  : écarté ; gardé pour ne pas le reproposer au prochain tour
  status      TEXT    NOT NULL DEFAULT 'draft'
              CHECK (status IN ('draft','validated','rejected')),

  -- Le code de partage vivait sur `theme`. Il descend ici : c'est ce
  -- sujet-là qu'un élève partage, pas le domaine entier.
  code        TEXT,
  exercise_count   INTEGER NOT NULL DEFAULT 0,
  subscriber_count INTEGER NOT NULL DEFAULT 0,

  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
  published_at TEXT,
  visibility  TEXT NOT NULL DEFAULT 'private'
              CHECK (visibility IN ('private','pending','public')),

  CHECK (parent_id IS NULL OR parent_id <> id),
  CHECK (depth >= 0)
);

-- ---------------------------------------------------------------------
-- exercise_prompt — une section de l'article, et ce qu'elle a produit
-- ---------------------------------------------------------------------

CREATE TABLE exercise_prompt_neuf (
  id          INTEGER PRIMARY KEY,
  chapter_id  INTEGER NOT NULL REFERENCES chapter_neuf (id) ON DELETE CASCADE,

  -- Les sections d'un article forment un arbre, et il est recopié ici
  -- tel quel : une section sans sous-section porte son contenu ; une
  -- section qui en a n'est qu'un titre, et ses sous-sections sont ses
  -- enfants. Le contenu vit donc toujours sur les feuilles, et c'est
  -- une feuille qui produit des exercices.
  parent_id   INTEGER          REFERENCES exercise_prompt_neuf (id) ON DELETE CASCADE,
  depth       INTEGER NOT NULL DEFAULT 0,
  -- L'ordre dans l'article, toutes sections confondues : c'est ce qui
  -- rend `position` unique par chapitre malgré l'arbre, et ce qui
  -- permet de restituer le plan de l'article dans l'ordre où il se lit.
  position    INTEGER NOT NULL DEFAULT 0,

  -- Le titre de la section, tel qu'il est dans l'article.
  title       TEXT NOT NULL,
  -- Son contenu, NULL sur les nœuds qui ont des enfants. C'est LA
  -- SOURCE : elle sert à écrire, jamais à afficher. Wikipédia est en
  -- CC BY-SA — écrire d'après elle ne pose rien, la recopier à l'élève
  -- poserait un problème d'attribution.
  content     TEXT,

  -- La consigne bâtie depuis title + content, telle qu'envoyée au modèle.
  rendered_prompt TEXT,
  model           TEXT,
  requested_count INTEGER NOT NULL DEFAULT 10,
  produced_count  INTEGER NOT NULL DEFAULT 0,
  status          TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','running','done','failed')),
  error           TEXT,

  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at TEXT,

  UNIQUE (chapter_id, position),
  CHECK (parent_id IS NULL OR parent_id <> id),
  CHECK (depth >= 0)
);

-- ---------------------------------------------------------------------
-- exercise — inchangé, sauf qu'il pend à un chapitre
-- ---------------------------------------------------------------------

CREATE TABLE exercise_neuf (
  id                 INTEGER PRIMARY KEY,
  chapter_id         INTEGER NOT NULL REFERENCES chapter_neuf (id) ON DELETE CASCADE,
  exercise_prompt_id INTEGER          REFERENCES exercise_prompt_neuf (id) ON DELETE SET NULL,
  sign_id            INTEGER          REFERENCES sign (id) ON DELETE SET NULL,

  type_question TEXT NOT NULL
                CHECK (type_question IN ('qcm','true_false','complete','find_error',
                                         'reorder','short_answer','cloze')),

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

-- ---------------------------------------------------------------------
-- Côté élève — ce à quoi il s'abonne et ce qu'il répond devient le
-- chapitre, puisque c'est l'ancien « thème » qu'il voyait à l'écran.
-- ---------------------------------------------------------------------

CREATE TABLE attempt_neuf (
  id           INTEGER PRIMARY KEY,
  user_id      INTEGER NOT NULL REFERENCES app_user (id)   ON DELETE CASCADE,
  exercise_id  INTEGER NOT NULL REFERENCES exercise_neuf (id) ON DELETE CASCADE,
  chapter_id   INTEGER NOT NULL REFERENCES chapter_neuf (id) ON DELETE CASCADE,
  -- NULL = exercice passé au swipe sans répondre.
  chosen_index INTEGER,
  is_correct   INTEGER,
  answer_ms    INTEGER,
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE user_chapter (
  user_id    INTEGER NOT NULL REFERENCES app_user (id)   ON DELETE CASCADE,
  chapter_id INTEGER NOT NULL REFERENCES chapter_neuf (id) ON DELETE CASCADE,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (user_id, chapter_id)
);

-- ---------------------------------------------------------------------
-- L'échange
-- ---------------------------------------------------------------------

DROP TABLE exercise;
DROP TABLE exercise_prompt;
DROP TABLE chapter;
DROP TABLE attempt;
DROP TABLE user_theme;
DROP TABLE theme_tag;
DROP TABLE tag;
DROP TABLE theme;
DROP TABLE category;

ALTER TABLE theme_neuf           RENAME TO theme;
ALTER TABLE chapter_neuf         RENAME TO chapter;
ALTER TABLE exercise_prompt_neuf RENAME TO exercise_prompt;
ALTER TABLE exercise_neuf        RENAME TO exercise;
ALTER TABLE attempt_neuf         RENAME TO attempt;

-- ---------------------------------------------------------------------
-- Index
-- ---------------------------------------------------------------------

CREATE INDEX ix_theme_position ON theme (status, position);

-- Une racine par thème, et rien qu'une. Index PARTIEL : il n'indexe
-- que les lignes sans parent, donc l'unicité ne porte que sur elles.
CREATE UNIQUE INDEX ux_chapter_root   ON chapter (theme_id) WHERE parent_id IS NULL;
CREATE UNIQUE INDEX ux_chapter_code   ON chapter (code)     WHERE code IS NOT NULL;
CREATE INDEX ix_chapter_theme  ON chapter (theme_id, status);
CREATE INDEX ix_chapter_parent ON chapter (parent_id);
CREATE INDEX ix_chapter_depth  ON chapter (theme_id, depth);
CREATE INDEX ix_chapter_feed   ON chapter (visibility, theme_id);

CREATE INDEX ix_exercise_prompt_chapter ON exercise_prompt (chapter_id, status);
CREATE INDEX ix_exercise_prompt_parent  ON exercise_prompt (parent_id);

CREATE INDEX ix_exercise_chapter ON exercise (chapter_id, state);
CREATE INDEX ix_exercise_state   ON exercise (state, id);
CREATE INDEX ix_exercise_sign    ON exercise (sign_id);
CREATE INDEX ix_exercise_run     ON exercise (exercise_prompt_id);

CREATE INDEX ix_attempt_exercise ON attempt (exercise_id);
CREATE INDEX ix_attempt_progress ON attempt (user_id, chapter_id, is_correct);
CREATE INDEX ix_attempt_rank     ON attempt (chapter_id, created_at, user_id);
CREATE INDEX ix_attempt_recent   ON attempt (user_id, created_at);

CREATE INDEX ix_user_chapter_chapter ON user_chapter (chapter_id);

-- ---------------------------------------------------------------------
-- Déclencheur et vues, reposés sur le nouveau vocabulaire
-- ---------------------------------------------------------------------

CREATE TRIGGER tg_chapter_touch
AFTER UPDATE ON chapter FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
  UPDATE chapter SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE VIEW v_exercise_health AS
SELECT e.id AS exercise_id, e.chapter_id, e.state, e.up_count, e.down_count,
       e.up_count + e.down_count AS votes,
       CASE WHEN e.up_count + e.down_count = 0 THEN NULL
            ELSE ROUND(100.0 * e.down_count / (e.up_count + e.down_count)) END AS down_pct,
       CASE WHEN e.up_count + e.down_count >= 5 AND e.down_count > e.up_count
            THEN 1 ELSE 0 END AS should_quarantine
FROM exercise e;

CREATE VIEW v_user_chapter_progress AS
SELECT
  a.user_id,
  a.chapter_id,
  COUNT(DISTINCT CASE WHEN a.is_correct = 1 THEN a.exercise_id END) AS passed,
  (SELECT COUNT(*) FROM exercise e
     WHERE e.chapter_id = a.chapter_id AND e.state = 'validated')   AS total,
  CAST(ROUND(
    100.0 * COUNT(DISTINCT CASE WHEN a.is_correct = 1 THEN a.exercise_id END)
    / NULLIF((SELECT COUNT(*) FROM exercise e
                WHERE e.chapter_id = a.chapter_id AND e.state = 'validated'), 0)
  ) AS INTEGER)                                                     AS pct
FROM attempt a
GROUP BY a.user_id, a.chapter_id;

CREATE VIEW v_global_rank AS
SELECT
  a.user_id,
  SUM(CASE WHEN a.is_correct = 1 THEN 10
           WHEN a.is_correct = 0 THEN 2
           ELSE 0 END)                                       AS points,
  SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END)          AS passed,
  COUNT(*)                                                   AS attempts
FROM attempt a
GROUP BY a.user_id;

CREATE VIEW v_chapter_week_rank AS
SELECT
  a.chapter_id,
  a.user_id,
  date(a.created_at, '-' || ((CAST(strftime('%w', a.created_at) AS INTEGER) + 6) % 7) || ' days')
    AS week_start,
  SUM(CASE WHEN a.is_correct = 1 THEN 10
           WHEN a.is_correct = 0 THEN 2
           ELSE 0 END)                                            AS points,
  SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END)               AS passed,
  SUM(CASE WHEN a.chosen_index IS NOT NULL THEN 1 ELSE 0 END)     AS answered
FROM attempt a
GROUP BY a.chapter_id, a.user_id, week_start;

DROP TABLE _controle_020;

COMMIT;

PRAGMA integrity_check;
PRAGMA foreign_key_check;
