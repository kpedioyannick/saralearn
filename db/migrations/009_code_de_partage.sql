-- Le code de partage.
--
-- Six caractères qu'on dicte à voix haute — dans une classe, au
-- téléphone, sur une diapositive. Il ouvre le quiz même privé : c'est le
-- geste « voici mon code, jouez-le » sans rien publier au catalogue.
--
-- Pourquoi pas `slug` : il existe déjà et il est unique, mais il est
-- dérivé du titre — `accord-du-participe-passe-passe-compose-cm2` — donc
-- illisible, indictable, et il changerait avec le titre. Un code se
-- donne une fois et ne doit plus bouger.
--
-- L'alphabet est posé côté Python (`api/codes.py`) et non ici : SQLite
-- ne sait pas tirer au hasard sans biais, et surtout la contrainte qui
-- compte est l'unicité, que la colonne porte.
--
-- Nullable exprès : une connaissance créée avant cette migration en
-- reçoit un par le remplissage ci-dessous, mais la colonne doit accepter
-- l'absence le temps de l'insertion.

ALTER TABLE theme ADD COLUMN code TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS ux_theme_code ON theme (code);
