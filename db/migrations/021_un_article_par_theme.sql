-- =====================================================================
-- 021 — l'unicité porte sur le couple (thème, article), pas sur l'article
--
-- La 020 posait `source_url UNIQUE` sur toute la table. C'était la règle
-- du déjà-vu, et elle marchait pour ce qu'on lui demandait : couper les
-- doublons et les cycles du crawl.
--
-- À l'usage, elle décidait autre chose sans le dire. LE PREMIER THÈME
-- CRAWLÉ CONFISQUAIT L'ARTICLE. « The Sky » a pris « Variable star » et
-- ses 53 descendants ; « The Stars », crawlé après, ne pouvait plus les
-- avoir. L'ordre des thèmes tranchait un partage que personne n'avait
-- arbitré.
--
-- L'unicité passe donc sur le couple. Un article peut vivre sous deux
-- thèmes — « Tide » appartient à la Lune comme à la Terre, et c'est
-- juste — mais jamais deux fois sous le même. Le crawl garde exactement
-- la garantie dont il a besoin : à l'intérieur d'un thème il ne tourne
-- pas en rond, et il s'épuise.
--
-- CE QUE ÇA COÛTE : le contenu d'un article partagé sera lu deux fois et
-- ses sections écrites deux fois. C'est le prix d'un arbre par thème
-- plutôt qu'un seul graphe découpé arbitrairement.
--
-- CE QUE ÇA DÉBLOQUE, en passant : deux thèmes peuvent être crawlés en
-- même temps sans se disputer un article. La contrainte ne les met plus
-- en concurrence.
--
-- SQLite ne sait pas retirer une contrainte de colonne : `source_url
-- TEXT UNIQUE` a créé un index implicite qu'aucun DROP INDEX n'atteint.
-- Il faut reconstruire la table. Les 635 chapitres déjà semés sont
-- effacés — ils l'auraient été de toute façon, puisqu'ils ont été
-- construits sous l'ancienne règle et que les caches rendent la reprise
-- quasi gratuite.
--
--   python3 scripts/migrate.py db/migrations/021_un_article_par_theme.sql
-- =====================================================================

BEGIN;

-- `exercise_prompt` et `exercise` référencent `chapter`. Toutes deux sont
-- vides — le contrôle plus bas s'en assure avant le moindre DROP.
CREATE TEMP TABLE _controle_021 (
  test TEXT    NOT NULL,
  ok   INTEGER NOT NULL CHECK (ok = 1)
);
INSERT INTO _controle_021 (test, ok)
SELECT 'aucun exercice ni section ne pend aux chapitres',
       (SELECT COUNT(*) FROM exercise) + (SELECT COUNT(*) FROM exercise_prompt) = 0;

DROP TABLE chapter;

CREATE TABLE chapter (
  id          INTEGER PRIMARY KEY,
  theme_id    INTEGER NOT NULL REFERENCES theme (id) ON DELETE CASCADE,

  -- NULL = racine du thème. L'index partiel plus bas en interdit deux.
  parent_id   INTEGER          REFERENCES chapter (id) ON DELETE CASCADE,
  depth       INTEGER NOT NULL DEFAULT 0,
  position    INTEGER NOT NULL DEFAULT 0,

  slug        TEXT    NOT NULL UNIQUE,
  title       TEXT    NOT NULL,
  description TEXT,

  -- Plus d'unicité ici : elle est sur le couple, voir ux_chapter_source.
  source_url  TEXT,
  -- {"wikipedia": "…", "pageid": 123, "revision": 456,
  --  "related": ["…"], "fetched_at": "…"}
  meta        TEXT    CHECK (meta IS NULL OR json_valid(meta)),

  status      TEXT    NOT NULL DEFAULT 'draft'
              CHECK (status IN ('draft','validated','rejected')),

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

-- LA CONTRAINTE DE CETTE MIGRATION. Partielle : une ligne sans
-- `source_url` — un chapitre écrit à la main, sans article — n'entre pas
-- dans le compte et ne bloque personne.
CREATE UNIQUE INDEX ux_chapter_source ON chapter (theme_id, source_url)
  WHERE source_url IS NOT NULL;

CREATE UNIQUE INDEX ux_chapter_root ON chapter (theme_id) WHERE parent_id IS NULL;
CREATE UNIQUE INDEX ux_chapter_code ON chapter (code)     WHERE code IS NOT NULL;
CREATE INDEX ix_chapter_theme  ON chapter (theme_id, status);
CREATE INDEX ix_chapter_parent ON chapter (parent_id);
CREATE INDEX ix_chapter_depth  ON chapter (theme_id, depth);
CREATE INDEX ix_chapter_feed   ON chapter (visibility, theme_id);

CREATE TRIGGER tg_chapter_touch
AFTER UPDATE ON chapter FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
  UPDATE chapter SET updated_at = datetime('now') WHERE id = NEW.id;
END;

DROP TABLE _controle_021;

COMMIT;

PRAGMA integrity_check;
PRAGMA foreign_key_check;
