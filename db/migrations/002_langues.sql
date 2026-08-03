-- =====================================================================
-- 002 — français et anglais
--
-- Deux langues, sur deux plans distincts :
--
--   · la TAXONOMIE est traduite — une catégorie « Langues » s'affiche
--     « Languages » en anglais. Colonne label_en plutôt qu'une table de
--     traductions : deux langues annoncées, et une jointure de moins
--     sur le chemin du feed. À revoir si une troisième arrive.
--
--   · un THÈME n'est pas traduit, il est ÉCRIT dans une langue. Son
--     cours et ses exercices sont en français ou en anglais, et on ne
--     sert jamais à un anglophone un exercice rédigé en français.
--
--   sqlite3 data/sara.db < db/migrations/002_langues.sql
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Taxonomie traduite
-- ---------------------------------------------------------------------

ALTER TABLE category     ADD COLUMN label_en TEXT;
ALTER TABLE sub_category ADD COLUMN label_en TEXT;

-- ---------------------------------------------------------------------
-- Langue de rédaction d'un thème
-- ---------------------------------------------------------------------

ALTER TABLE theme ADD COLUMN lang TEXT NOT NULL DEFAULT 'fr'
  CHECK (lang IN ('fr', 'en'));

CREATE INDEX IF NOT EXISTS ix_theme_lang ON theme (lang, visibility);

-- Le feed filtre sur (langue, état, thème) : l'index doit porter la
-- langue, sinon on scanne tous les exercices des deux langues.
DROP INDEX IF EXISTS ix_exercise_feed;
CREATE INDEX ix_exercise_feed ON exercise (theme_id, state, type_bloom);

-- ---------------------------------------------------------------------
-- Langue de l'utilisateur
-- ---------------------------------------------------------------------

ALTER TABLE app_user ADD COLUMN lang TEXT NOT NULL DEFAULT 'fr'
  CHECK (lang IN ('fr', 'en'));

-- ---------------------------------------------------------------------
-- Les gabarits de prompt sont eux aussi propres à une langue :
-- on ne demande pas un exercice français avec des consignes anglaises.
-- ---------------------------------------------------------------------

-- L'unicité (type_question, type_bloom, version) doit désormais inclure
-- la langue. SQLite ne sait pas modifier une contrainte : il faut
-- recréer la table et recopier. Les clés étrangères sont suspendues le
-- temps de l'échange, puis revérifiées.
PRAGMA foreign_keys = OFF;

CREATE TABLE prompt_new (
  id            INTEGER PRIMARY KEY,
  lang          TEXT NOT NULL DEFAULT 'fr' CHECK (lang IN ('fr','en')),
  type_question TEXT NOT NULL
                CHECK (type_question IN ('qcm','true_false','complete','find_error','reorder')),
  type_bloom    TEXT NOT NULL
                CHECK (type_bloom IN ('remember','understand','apply','analyze')),
  version       INTEGER NOT NULL DEFAULT 1,
  is_active     INTEGER NOT NULL DEFAULT 1,
  label         TEXT NOT NULL,
  template      TEXT NOT NULL,
  output_schema TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (lang, type_question, type_bloom, version)
);

INSERT INTO prompt_new
  (id, lang, type_question, type_bloom, version, is_active, label, template, output_schema, created_at)
SELECT id, 'fr', type_question, type_bloom, version, is_active, label, template, output_schema, created_at
FROM prompt;

DROP TABLE prompt;
ALTER TABLE prompt_new RENAME TO prompt;

CREATE INDEX ix_prompt_active ON prompt (is_active, lang, type_question, type_bloom);

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Libellés anglais de la taxonomie de démonstration
-- ---------------------------------------------------------------------

UPDATE category SET label_en = CASE slug
  WHEN 'langues' THEN 'Languages'
  WHEN 'mythes'  THEN 'Myths & history'
  WHEN 'vivant'  THEN 'Life sciences'
  WHEN 'musique' THEN 'Music'
  WHEN 'ciel'    THEN 'Sky & space'
  WHEN 'logique' THEN 'Logic'
  ELSE label END;

UPDATE sub_category SET label_en = CASE slug
  WHEN 'vocabulaire-anglais' THEN 'English vocabulary'
  WHEN 'faux-amis'           THEN 'False friends'
  WHEN 'mythologie-grecque'  THEN 'Greek mythology'
  WHEN 'rome-antique'        THEN 'Ancient Rome'
  WHEN 'corps-humain'        THEN 'Human body'
  WHEN 'cellules-adn'        THEN 'Cells & DNA'
  WHEN 'accords-guitare'     THEN 'Guitar chords'
  WHEN 'systeme-solaire'     THEN 'Solar system'
  ELSE label END;
