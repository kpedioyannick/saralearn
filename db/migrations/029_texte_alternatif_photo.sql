-- Le texte alternatif de la photo d'ambiance, oublié par la 028.
--
-- Il ne se déduit pas de `image_query` : la requête dit ce qu'on
-- CHERCHAIT, l'alternatif dit ce que la photo MONTRE, et Unsplash le
-- fournit avec elle (`alt_description`). L'écart compte ici : l'app lit
-- ses cartes à voix haute (`src/lib/spoken.ts`), et un lecteur d'écran
-- annoncerait « route vide chaude » là où la photo montre une autoroute
-- dans le désert.
--
-- Il n'est PAS traduit, et c'est délibéré : `exercise_translation` ne
-- porte que ce que l'élève lit. Une description d'image passée au
-- traducteur champ par champ donnerait le même genre de fautes que
-- « Droite ! » pour « Right! » — voir `api/titres.py`.

ALTER TABLE exercise ADD COLUMN image_alt TEXT;
