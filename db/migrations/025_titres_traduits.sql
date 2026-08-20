-- =====================================================================
-- 025 — les titres du catalogue dans la langue du lecteur
--
-- L'interface passait en français et le catalogue restait en anglais :
-- « Light · 146 apprentissages », « Aether drag hypothesis », « Sun dog ».
-- Les exercices, eux, étaient traduits depuis la migration 024. Le
-- catalogue est ce qu'on voit AVANT d'en ouvrir un seul.
--
-- Deux tables et pas une : un thème est un jour de la création, choisi et
-- écrit à la main ; un chapitre est un article de Wikipédia. Les deux ne
-- se traduisent pas de la même façon, et c'est le point de cette
-- migration.
--
--   · les 11 THÈMES sont posés ici, en clair, écrits par un humain. Onze
--     lignes ne valent pas un appel réseau, et « The Human Being » rendu
--     par une machine donnerait « L'être humain » ou « L'humain » selon
--     le jour. Ce sont les six jours de la création : leur nom est un
--     choix, pas une traduction ;
--
--   · les 2 187 CHAPITRES viennent des liens de langue de Wikipédia —
--     `scripts/traduire_titres.py`. Un article anglais qui a sa version
--     française donne son titre officiel : « 22° halo » devient « Halo à
--     22 degrés », pas ce qu'un traducteur automatique en ferait. C'est
--     exact par construction, et gratuit. Ce qui n'a pas d'article
--     français n'a pas de ligne, et reste affiché en anglais — mieux vaut
--     un titre anglais juste qu'un titre français inventé.
--
-- `source` garde qui a traduit : on doit pouvoir repasser sur ce qu'une
-- machine a produit sans toucher à ce qu'un humain a écrit.
-- =====================================================================

CREATE TABLE theme_translation (
  theme_id   INTEGER NOT NULL REFERENCES theme (id) ON DELETE CASCADE,
  lang       TEXT    NOT NULL,
  title      TEXT    NOT NULL,
  source     TEXT    NOT NULL DEFAULT 'humain',
  created_at TEXT    NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (theme_id, lang)
);

CREATE TABLE chapter_translation (
  chapter_id  INTEGER NOT NULL REFERENCES chapter (id) ON DELETE CASCADE,
  lang        TEXT    NOT NULL,
  title       TEXT    NOT NULL,
  description TEXT,
  source      TEXT    NOT NULL DEFAULT 'wikipedia-langlinks',
  created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (chapter_id, lang)
);

-- Les onze jours, nommés à la main.
INSERT INTO theme_translation (theme_id, lang, title, source)
SELECT id, 'fr',
       CASE title
         WHEN 'Light'           THEN 'La Lumière'
         WHEN 'The Sky'         THEN 'Le Ciel'
         WHEN 'The Earth'       THEN 'La Terre'
         WHEN 'Vegetation'      THEN 'La Végétation'
         WHEN 'The Sun'         THEN 'Le Soleil'
         WHEN 'The Moon'        THEN 'La Lune'
         WHEN 'The Stars'       THEN 'Les Étoiles'
         WHEN 'Marine Animals'  THEN 'Les Animaux marins'
         WHEN 'Birds'           THEN 'Les Oiseaux'
         WHEN 'Land Animals'    THEN 'Les Animaux terrestres'
         WHEN 'The Human Being' THEN 'L''Être humain'
       END,
       'humain'
  FROM theme
 WHERE title IN ('Light','The Sky','The Earth','Vegetation','The Sun','The Moon',
                 'The Stars','Marine Animals','Birds','Land Animals','The Human Being');
