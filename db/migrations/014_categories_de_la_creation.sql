-- =====================================================================
-- 014 — les six catégories de la création
--
-- SaraLearn change de matière. Le catalogue actuel enseigne des
-- compétences — conjuguer, orthographier, écrire une fonction PHP,
-- reconnaître un panneau. Le nouveau enseigne le monde : ce qui a été
-- créé, et comment cela fonctionne. Les questions deviennent du trivia
-- de culture générale, en un tap, sur ce qui entoure l'élève.
--
-- SIX CATÉGORIES, DANS L'ORDRE DES SIX JOURS. Le classement vient de la
-- Genèse ; la matière, elle, est le monde observable. On y parle de la
-- vitesse de la lumière, du vol des oiseaux, de la germination d'une
-- graine — jamais de ce que l'homme a fabriqué, mesuré ou nommé pour
-- son usage. Ni ampoule, ni télescope, ni fuseau horaire.
--
-- `lang = 'en'` ET NON `NULL`. Une catégorie sans langue vaut pour tout
-- le monde (`taxonomy.py` : `WHERE lang IS NULL OR lang = ?`), et c'est
-- ce qu'on voudra le jour où le contenu existera dans les deux langues.
-- Mais `theme.lang` est NOT NULL et le feed filtre sec dessus
-- (`feed.py` : `WHERE t.lang = ?`) : avec un contenu anglais seul, une
-- catégorie sans langue afficherait six étagères VIDES aux 166 comptes
-- francophones. On pose donc 'en' aujourd'hui, et le jour où le jumeau
-- français est généré, cette migration se prolonge d'un seul UPDATE.
--
-- `label` PORTE DÉJÀ LE FRANÇAIS, bien qu'il ne soit servi à personne
-- pour l'instant : `taxonomy.py` rend `COALESCE(label_en, label)` aux
-- anglophones et `label` aux francophones, or aucun francophone ne voit
-- ces lignes tant que `lang = 'en'`. On l'écrit quand même, parce que
-- c'est exactement ce qui rendra le basculement vers NULL gratuit.
--
-- CE QUI NE BOUGE PAS : les 10 catégories actuelles restent `active`
-- avec leurs 107 thèmes et 3 185 exercices. Leur retrait est décidé,
-- mais il emporte 483 tentatives de 51 utilisateurs et 124
-- abonnements ; il fera l'objet de la migration 015, quand la nouvelle
-- direction tiendra debout. Effacer avant d'avoir de quoi remplir
-- laisserait l'app vide.
--
-- AUCUN DDL ICI. Ni table créée, ni colonne ajoutée, ni contrainte
-- touchée : six INSERT. Le schéma actuel accepte tout ce que la
-- nouvelle direction demande, y compris de n'écrire que des QCM —
-- `type_bloom` reste NOT NULL et recevra toujours 'remember', une
-- constante qu'on retirera avec le reste en 015.
--
-- Les couleurs sont distinctes des six déjà en usage (#1B5E33, #1684D6,
-- #7A4FCB, #0F766E, #B45309, #BE123C) : deux catégories de même teinte
-- se confondent dans le rail de navigation.
--
--   python3 scripts/migrate.py db/migrations/014_categories_de_la_creation.sql
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- Les six jours
--
-- `position` reprend après le maximum actuel (8) et suit l'ordre des
-- jours : c'est le seul ordre qui ait un sens ici, et `taxonomy.py`
-- trie dessus avant le libellé.
-- ---------------------------------------------------------------------

INSERT INTO category (slug, label, label_en, color, position, lang, status) VALUES
  ('light-and-darkness',
   'Lumière et Obscurité',
   'Light and Darkness',
   '#CA8A04', 9,  'en', 'active'),

  ('the-sky',
   'Le Ciel',
   'The Sky',
   '#0284C7', 10, 'en', 'active'),

  ('earth-sea-and-vegetation',
   'La Terre, la Mer et les Végétaux',
   'The Earth, the Sea and Vegetation',
   '#15803D', 11, 'en', 'active'),

  ('sun-moon-and-stars',
   'Le Soleil, la Lune et les Étoiles',
   'The Sun, the Moon and the Stars',
   '#4338CA', 12, 'en', 'active'),

  ('animals',
   'Les Animaux',
   'The Animals',
   '#C2410C', 13, 'en', 'active'),

  ('the-human-being',
   'L''Être Humain',
   'The Human Being',
   '#9333EA', 14, 'en', 'active');


-- ---------------------------------------------------------------------
-- Vérifications
--
-- `RAISE(ABORT, ...)` n'existe QUE dans un trigger : hors trigger,
-- SQLite refuse de le compiler. Le seul moyen d'échouer volontairement
-- au milieu d'un script est donc de violer une contrainte — d'où cette
-- table temporaire qui n'accepte que la valeur 1. Chaque INSERT y écrit
-- le résultat d'un test ; un test faux lève une exception, `migrate.py`
-- l'attrape et restaure la sauvegarde.
--
-- La table est TEMP : elle meurt avec la connexion et ne laisse rien
-- derrière elle dans le schéma.
-- ---------------------------------------------------------------------

CREATE TEMP TABLE _controle_014 (
  test TEXT    NOT NULL,
  ok   INTEGER NOT NULL CHECK (ok = 1)
);

-- Les six sont entrées, actives et anglaises.
INSERT INTO _controle_014 (test, ok)
SELECT 'les six catégories sont en base',
       (SELECT COUNT(*) FROM category
         WHERE lang = 'en' AND status = 'active'
           AND slug IN ('light-and-darkness', 'the-sky',
                        'earth-sea-and-vegetation', 'sun-moon-and-stars',
                        'animals', 'the-human-being')) = 6;

-- Aucun slug en double : rien ne contraint leur unicité au niveau du
-- schéma, et deux catégories homonymes se distinguent mal dans le rail.
INSERT INTO _controle_014 (test, ok)
SELECT 'aucun slug de catégorie en double',
       NOT EXISTS (SELECT 1 FROM category GROUP BY slug HAVING COUNT(*) > 1);

-- Les dix anciennes sont intactes : cette migration n'en supprime
-- aucune, et un compte qui aurait bougé signale une erreur de copie.
INSERT INTO _controle_014 (test, ok)
SELECT 'les dix anciennes catégories sont intactes',
       (SELECT COUNT(*) FROM category WHERE position <= 8) = 10;

-- Aucun thème n'a changé de catégorie.
INSERT INTO _controle_014 (test, ok)
SELECT 'aucun thème n''a bougé',
       (SELECT COUNT(*) FROM theme) = 107;

COMMIT;
