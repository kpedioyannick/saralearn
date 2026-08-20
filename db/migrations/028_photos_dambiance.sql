-- Une photo d'ambiance par exercice — la SCÈNE, jamais le phénomène.
--
-- Le rail d'image existait déjà, mais pour des pictogrammes : `exercise.
-- sign_id` pointait la table `sign` du catalogue de panneaux routiers,
-- vide depuis que ses 619 SVG ont été perdus. On ne le réutilise pas :
-- un panneau est une ressource partagée entre exercices et décrite par
-- un code, une photo d'ambiance appartient à sa question et se décrit
-- par son crédit. Quatre colonnes valent mieux qu'une jointure sur une
-- table dont aucune colonne ne sert.
--
-- L'URL est CELLE D'UNSPLASH, et pas un fichier local : leurs conditions
-- d'API imposent le lien direct vers leur CDN. C'est aussi ce qui rend
-- la chose gratuite et sans stockage.
--
-- `image_credit` et `image_credit_url` ne sont pas décoratifs : la
-- licence Unsplash n'exige pas l'attribution, mais LES CONDITIONS DE
-- LEUR API, si. Sans la ligne de crédit à l'écran, l'usage est hors
-- règles. C'est pourquoi les quatre colonnes vont ensemble, et pourquoi
-- le front affiche le crédit dès qu'il y a une photo.
--
-- `image_query` garde les mots qui ont trouvé la photo. Ce n'est pas une
-- trace pour rien : c'est ce qui permet de rechercher plus tard sans
-- redemander au modèle, et de voir d'un coup d'oeil les requêtes qui
-- nomment le phénomène au lieu de la scène.

ALTER TABLE exercise ADD COLUMN image_query      TEXT;
ALTER TABLE exercise ADD COLUMN image_url        TEXT;
ALTER TABLE exercise ADD COLUMN image_credit     TEXT;
ALTER TABLE exercise ADD COLUMN image_credit_url TEXT;

-- Retrouver les exercices qui n'ont pas encore leur photo, sans balayer
-- la table : c'est la question que pose le remplissage en tâche de fond,
-- et il la pose à chaque passage.
CREATE INDEX IF NOT EXISTS idx_exercise_sans_photo
    ON exercise (state, image_url);
