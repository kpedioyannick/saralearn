-- =====================================================================
-- 005 — une sous-catégorie peut n'exister que dans une langue
--
-- Jusqu'ici `sub_category` était partagée entre les deux langues, avec
-- un simple `label_en` pour la traduire. Ça supposait que la taxonomie
-- est la même partout et que seuls les mots changent.
--
-- Vrai pour « Mythologie grecque », faux dès qu'on touche à une matière
-- scolaire : le français enseigne la CONJUGAISON comme discipline, le
-- programme américain ne la connaît pas — le verbe anglais est trop
-- simple pour la justifier, ses temps se traitent dans la grammaire.
-- Traduire « Conjugaison » en « Conjugation » afficherait à un
-- apprenant américain une matière qu'il ne chercherait jamais.
--
-- D'où `lang` : NULL = universelle, sinon propre à cette langue.
-- Même logique que `country` sur les thèmes.
--
--   sqlite3 data/sara.db < db/migrations/005_sous_categories_par_langue.sql
-- =====================================================================

PRAGMA foreign_keys = ON;

ALTER TABLE sub_category ADD COLUMN lang TEXT NULL
  CHECK (lang IS NULL OR lang IN ('fr', 'en'));

ALTER TABLE category ADD COLUMN lang TEXT NULL
  CHECK (lang IS NULL OR lang IN ('fr', 'en'));

CREATE INDEX IF NOT EXISTS ix_sub_category_lang ON sub_category (lang, category_id);
CREATE INDEX IF NOT EXISTS ix_category_lang ON category (lang, position);
