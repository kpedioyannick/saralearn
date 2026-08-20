-- =====================================================================
-- 016 — purge de l'ancien catalogue
--
-- La migration 014 a posé les six catégories de la création et le semis
-- leurs 36 thèmes et 196 chapitres. Celle-ci retire le monde d'avant :
-- dix catégories qui enseignaient des compétences — conjuguer,
-- orthographier, écrire une fonction PHP, reconnaître un panneau — et
-- tout ce qu'elles portaient.
--
-- CE N'EST PAS DU RANGEMENT. Tant que l'ancien catalogue est là,
-- `GET /tags` propose « cm2 » et « git » à qui crée un thème sur les
-- oiseaux, `/credits` publie les crédits de 785 panneaux que plus rien
-- n'affiche, et l'app montre seize catégories dont dix hors sujet.
--
-- PERSONNE N'EST DÉLOGÉ. La base compte 365 comptes, mais 301 sont des
-- sessions anonymes et 63 des 64 inscrits portent une adresse d'essai
-- (@exemple.fr, @exemple.test, @demo.com) semée par les tests. Il reste
-- UN compte réel, id 8, déjà en anglais. C'est ce qui autorise une
-- purge franche plutôt qu'une migration de données.
--
-- ---------------------------------------------------------------------
-- L'ORDRE DES SUPPRESSIONS N'EST PAS NÉGOCIABLE
--
-- Deux contraintes du schéma VIVANT le fixent — vérifiées en rejouant
-- le DDL réel, pas en lisant `db/schema.sql`, qui est le schéma
-- d'origine et ignore tout ce que les migrations 002 à 015 ont posé.
--
--   1. `theme.category_id` est NOT NULL REFERENCES category (id), SANS
--      clause ON DELETE. Supprimer une catégorie qui porte encore un
--      thème lève « FOREIGN KEY constraint failed ».
--      → les thèmes passent AVANT les catégories.
--
--   2. `exercise_prompt` porte CHECK (prompt_id IS NOT NULL OR
--      chapter_id IS NOT NULL), et `exercise_prompt.chapter_id` est
--      ON DELETE SET NULL. 330 des 485 lignes condamnées ont
--      `prompt_id IS NULL` : supprimer leurs chapitres d'abord mettrait
--      `chapter_id` à NULL et violerait le CHECK.
--      → les lancements passent AVANT les chapitres.
--
-- ON NE COMPTE PAS SUR LES CASCADES. `scripts/migrate.py` ouvre sa
-- connexion sans `PRAGMA foreign_keys`, et SQLite le laisse à OFF par
-- défaut : un DELETE sur `theme` ne déclencherait aucune cascade et
-- laisserait 3 185 exercices orphelins. On supprime donc chaque table
-- explicitement, des feuilles vers la racine. Le PRAGMA est posé quand
-- même — ceinture et bretelles — et `migrate.py` passe un
-- `foreign_key_check` après coup qui restaurerait la base au moindre
-- orphelin.
--
-- ---------------------------------------------------------------------
-- CE QUI SURVIT, ET POURQUOI
--
--   · les gabarits 41 et 42, « Rédaction directe — sans gabarit ». Le 42
--     est vital : tout le nouveau contenu entre par lui
--     (`scripts/import_exercises.py` le retrouve PAR SON LIBELLÉ), et
--     l'unique `exercise_prompt` restant pointe dessus.
--   · la TABLE `sign`, vidée mais conservée. La supprimer obligerait à
--     recréer `exercise` une deuxième fois pour retirer sa clé
--     `sign_id` — la manœuvre la plus risquée du dépôt, pour ranger une
--     table vide. Les jointures `LEFT JOIN sign` de `feed.py` et
--     `generate.py` continuent de répondre, désormais toujours NULL, et
--     `to_exercise_out` lit `sign_image` sans valeur de repli : cette
--     table doit rester debout.
--   · le compte id 8.
--
--   python3 scripts/migrate.py db/migrations/016_purge_de_l_ancien_catalogue.sql
-- =====================================================================

PRAGMA foreign_keys = ON;

BEGIN;

-- ---------------------------------------------------------------------
-- La liste des condamnés, figée une fois pour toutes
--
-- Chaque DELETE s'y réfère. Sans elle, le dernier porterait sur une
-- jointure `theme → category` dont la moitié aurait déjà disparu, et ne
-- trouverait plus rien à supprimer.
--
-- Le critère est le slug des SIX QUI RESTENT, pas celui des dix qui
-- partent : une catégorie oubliée dans une liste de dix survivrait par
-- accident, alors qu'ici tout ce qui n'est pas nommé tombe.
-- ---------------------------------------------------------------------

CREATE TEMP TABLE _condamnes AS
SELECT t.id
  FROM theme t
  JOIN category c ON c.id = t.category_id
 WHERE c.slug NOT IN ('light-and-darkness', 'the-sky',
                      'earth-sea-and-vegetation', 'sun-moon-and-stars',
                      'animals', 'the-human-being');


-- ---------------------------------------------------------------------
-- Contrôles AVANT le premier DELETE
--
-- `RAISE(ABORT, ...)` n'existe que dans un trigger : hors trigger,
-- SQLite refuse de le compiler. Pour échouer volontairement au milieu
-- d'un script, on viole une contrainte — cette table temporaire
-- n'accepte que la valeur 1.
--
-- Ces trois tests sont placés ICI, avant toute suppression : si l'un
-- tombe, la transaction meurt alors que la base est encore intacte.
-- ---------------------------------------------------------------------

CREATE TEMP TABLE _controle_016 (
  test TEXT    NOT NULL,
  ok   INTEGER NOT NULL CHECK (ok = 1)
);

INSERT INTO _controle_016 (test, ok)
SELECT '107 thèmes condamnés, ni plus ni moins',
       (SELECT COUNT(*) FROM _condamnes) = 107;

-- Aucun thème des six nouvelles catégories n'a été pris dans la liste.
INSERT INTO _controle_016 (test, ok)
SELECT 'les 36 thèmes de la création sont hors de la liste',
       NOT EXISTS (
         SELECT 1 FROM _condamnes d
           JOIN theme t    ON t.id = d.id
           JOIN category c ON c.id = t.category_id
          WHERE c.slug IN ('light-and-darkness', 'the-sky',
                           'earth-sea-and-vegetation', 'sun-moon-and-stars',
                           'animals', 'the-human-being'));

-- Le compte à conserver existe bien. Sans ce test, une adresse mal
-- orthographiée plus bas viderait `app_user` en entier.
INSERT INTO _controle_016 (test, ok)
SELECT 'le compte à conserver existe',
       (SELECT COUNT(*) FROM app_user
         WHERE email = 'yannick.kpedio@gmail.com') = 1;

-- Les deux gabarits de rédaction directe sont là. `import_exercises.py`
-- les retrouve par leur libellé ; s'ils manquaient, la clause de
-- conservation plus bas ne protégerait rien.
INSERT INTO _controle_016 (test, ok)
SELECT 'les deux gabarits de rédaction directe sont là',
       (SELECT COUNT(*) FROM prompt WHERE version = 999) = 2;


-- ---------------------------------------------------------------------
-- Suppression, des feuilles vers la racine
-- ---------------------------------------------------------------------

DELETE FROM exercise_vote
 WHERE exercise_id IN (SELECT id FROM exercise
                        WHERE theme_id IN (SELECT id FROM _condamnes));

DELETE FROM exercise_comment
 WHERE exercise_id IN (SELECT id FROM exercise
                        WHERE theme_id IN (SELECT id FROM _condamnes));

DELETE FROM attempt         WHERE theme_id IN (SELECT id FROM _condamnes);
DELETE FROM exercise        WHERE theme_id IN (SELECT id FROM _condamnes);

-- Avant `chapter` : voir l'en-tête, le CHECK d'`exercise_prompt`.
DELETE FROM exercise_prompt WHERE theme_id IN (SELECT id FROM _condamnes);
DELETE FROM chapter         WHERE theme_id IN (SELECT id FROM _condamnes);

DELETE FROM theme_tag       WHERE theme_id IN (SELECT id FROM _condamnes);
DELETE FROM user_theme      WHERE theme_id IN (SELECT id FROM _condamnes);
DELETE FROM theme           WHERE id       IN (SELECT id FROM _condamnes);

-- Les catégories en dernier : jusqu'ici elles portaient encore des
-- thèmes, et `theme.category_id` n'a pas d'ON DELETE.
DELETE FROM category
 WHERE slug NOT IN ('light-and-darkness', 'the-sky',
                    'earth-sea-and-vegetation', 'sun-moon-and-stars',
                    'animals', 'the-human-being');


-- ---------------------------------------------------------------------
-- Les orphelins
-- ---------------------------------------------------------------------

-- Les 182 liens `theme_tag` sont partis avec les thèmes ; il reste 106
-- étiquettes que plus rien ne porte. Elles ne cassent rien, mais
-- `GET /tags` sert la liste entière à l'autocomplétion : sans élagage,
-- on proposerait « cm2 » ou « git » sous une catégorie sur les animaux.
DELETE FROM tag
 WHERE id NOT IN (SELECT tag_id FROM theme_tag);

-- Les 785 panneaux routiers. Leurs 439 exercices appartenaient tous au
-- permis de conduire et viennent de disparaître. La TABLE reste — voir
-- l'en-tête —, seules ses lignes s'en vont. Les 9,7 Mo de `media/signs`
-- se retirent à la main, hors migration.
DELETE FROM sign;

-- Les 40 gabarits de génération de l'ancien catalogue. `version <> 999`
-- épargne exactement les deux gabarits de rédaction directe, dont le
-- 42 par lequel entre tout le nouveau contenu.
DELETE FROM prompt WHERE version <> 999;

-- Les 63 comptes d'essai et les 301 sessions anonymes.
--
-- `IS NOT` ET NON `<>`. En SQL, `NULL <> 'x'` vaut NULL, donc faux :
-- un `<>` aurait épargné les 301 anonymes, dont l'adresse est NULL.
-- L'opérateur `IS NOT` de SQLite compare en traitant NULL comme une
-- valeur — `NULL IS NOT 'x'` vaut vrai — et les emporte.
DELETE FROM app_user
 WHERE email IS NOT 'yannick.kpedio@gmail.com';


-- ---------------------------------------------------------------------
-- Contrôles APRÈS
-- ---------------------------------------------------------------------

INSERT INTO _controle_016 (test, ok)
SELECT 'six catégories, et ce sont les bonnes',
       (SELECT COUNT(*) FROM category) = 6
   AND (SELECT COUNT(*) FROM category
         WHERE slug IN ('light-and-darkness', 'the-sky',
                        'earth-sea-and-vegetation', 'sun-moon-and-stars',
                        'animals', 'the-human-being')) = 6;

INSERT INTO _controle_016 (test, ok)
SELECT '36 thèmes et 196 chapitres intacts',
       (SELECT COUNT(*) FROM theme) = 36 AND (SELECT COUNT(*) FROM chapter) = 196;

-- Le premier chapitre écrit est toujours là, avec son lancement.
INSERT INTO _controle_016 (test, ok)
SELECT 'les 10 exercices de Birds ont survécu',
       (SELECT COUNT(*) FROM exercise) = 10
   AND (SELECT COUNT(*) FROM exercise e JOIN theme t ON t.id = e.theme_id
         WHERE t.slug = 'birds' AND e.state = 'validated') = 10;

-- Le gabarit 42 est là ET son lancement pointe toujours dessus :
-- `exercise_prompt.prompt_id` est NO ACTION, une erreur ici aurait
-- laissé une référence morte plutôt qu'une erreur franche.
INSERT INTO _controle_016 (test, ok)
SELECT 'la chaîne de rédaction directe est intacte',
       (SELECT COUNT(*) FROM prompt) = 2
   AND (SELECT COUNT(*) FROM exercise_prompt ep
          JOIN prompt p ON p.id = ep.prompt_id
         WHERE p.version = 999) = 1;

INSERT INTO _controle_016 (test, ok)
SELECT 'un seul compte, le bon',
       (SELECT COUNT(*) FROM app_user) = 1
   AND (SELECT COUNT(*) FROM app_user
         WHERE email = 'yannick.kpedio@gmail.com') = 1;

INSERT INTO _controle_016 (test, ok)
SELECT 'plus rien de l''ancien monde',
       (SELECT COUNT(*) FROM attempt)    = 0
   AND (SELECT COUNT(*) FROM user_theme) = 0
   AND (SELECT COUNT(*) FROM theme_tag)  = 0
   AND (SELECT COUNT(*) FROM tag)        = 0
   AND (SELECT COUNT(*) FROM sign)       = 0
   AND (SELECT COUNT(*) FROM exercise_vote)    = 0
   AND (SELECT COUNT(*) FROM exercise_comment) = 0;

-- Aucun thème ne pointe sur une catégorie disparue. `foreign_key_check`
-- de `migrate.py` le dirait aussi, mais il parle après le COMMIT ; ici
-- la transaction peut encore être annulée.
INSERT INTO _controle_016 (test, ok)
SELECT 'aucune référence morte vers category',
       NOT EXISTS (SELECT 1 FROM theme t
                    LEFT JOIN category c ON c.id = t.category_id
                    WHERE c.id IS NULL);

COMMIT;
