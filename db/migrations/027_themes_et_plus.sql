-- =====================================================================
-- 027 — « et plus » au nom des thèmes, et la racine en tête
--
-- LE PROBLÈME. Le thème « La Terre » et le chapitre « Terre » sont deux
-- choses différentes qui portent le même mot. Le premier est un jour de
-- la création, un classeur nommé à la main en 025. Le second est
-- l'article `en.wikipedia.org/wiki/Earth`, celui d'où part le crawl —
-- la racine de l'arbre, 35 enfants directs, 300 descendants.
--
-- Le catalogue les affichait à plat : « La Terre · 36 apprentissages »,
-- puis « Océan, Terre, Lune, Abiogenèse… ». Un parent rangé parmi ses
-- propres enfants, et deuxième, derrière « Océan » — les deux ont 35
-- enfants, l'alphabet a tranché. Ça se lisait comme une ligne en double.
-- Le cas touche cinq thèmes sur onze : Lumière, Ciel, Terre, Soleil,
-- Lune.
--
-- LE CHOIX. On renomme le CLASSEUR, pas l'article. Le nom du thème est
-- déjà un choix humain — c'est tout le propos de 025, qui refusait de
-- laisser une machine décider si « The Human Being » donne « L'être
-- humain » ou « L'humain ». Le titre du chapitre, lui, doit rester
-- fidèle à son article : dix fichiers s'en servent pour retrouver la
-- source, écrire les questions et traduire les titres.
--
-- « La Terre et plus » dit exactement ce que le classeur contient : cet
-- article, et ce qui pend dessous. Trouver « Terre » à l'intérieur n'est
-- plus un doublon, c'est ce que le nom annonçait.
--
-- LES DEUX LANGUES. `theme_translation` sert de nom d'AFFICHAGE, pas
-- seulement de traduction : la jointure de `_SELECT` prend `lang = ?`,
-- donc une ligne `en` s'impose aussi au lecteur anglophone. C'est ce qui
-- permet de renommer sans toucher à `theme.title`, qui reste la clé sur
-- laquelle les migrations et `semer_creation.py` retrouvent leurs thèmes.
--
-- Écrit en clair et non par concaténation (`title || ' et plus'`) : une
-- migration rejouée doublerait le suffixe, et « La Terre et plus et
-- plus » ne se voit qu'à l'écran.
-- =====================================================================

-- Les onze noms français, réécrits en entier.
UPDATE theme_translation
   SET title = CASE (SELECT title FROM theme WHERE theme.id = theme_translation.theme_id)
         WHEN 'Light'           THEN 'La Lumière et plus'
         WHEN 'The Sky'         THEN 'Le Ciel et plus'
         WHEN 'The Earth'       THEN 'La Terre et plus'
         WHEN 'Vegetation'      THEN 'La Végétation et plus'
         WHEN 'The Sun'         THEN 'Le Soleil et plus'
         WHEN 'The Moon'        THEN 'La Lune et plus'
         WHEN 'The Stars'       THEN 'Les Étoiles et plus'
         WHEN 'Marine Animals'  THEN 'Les Animaux marins et plus'
         WHEN 'Birds'           THEN 'Les Oiseaux et plus'
         WHEN 'Land Animals'    THEN 'Les Animaux terrestres et plus'
         WHEN 'The Human Being' THEN 'L''Être humain et plus'
         ELSE title
       END,
       source = 'humain'
 WHERE lang = 'fr';

-- Et les onze noms anglais, qui n'avaient pas de ligne : l'anglais est
-- la langue source, il lisait `theme.title` directement.
INSERT OR REPLACE INTO theme_translation (theme_id, lang, title, source)
SELECT id, 'en',
       CASE title
         WHEN 'Light'           THEN 'Light and more'
         WHEN 'The Sky'         THEN 'The Sky and more'
         WHEN 'The Earth'       THEN 'The Earth and more'
         WHEN 'Vegetation'      THEN 'Vegetation and more'
         WHEN 'The Sun'         THEN 'The Sun and more'
         WHEN 'The Moon'        THEN 'The Moon and more'
         WHEN 'The Stars'       THEN 'The Stars and more'
         WHEN 'Marine Animals'  THEN 'Marine Animals and more'
         WHEN 'Birds'           THEN 'Birds and more'
         WHEN 'Land Animals'    THEN 'Land Animals and more'
         WHEN 'The Human Being' THEN 'The Human Being and more'
       END,
       'humain'
  FROM theme
 WHERE title IN ('Light','The Sky','The Earth','Vegetation','The Sun','The Moon',
                 'The Stars','Marine Animals','Birds','Land Animals','The Human Being');
