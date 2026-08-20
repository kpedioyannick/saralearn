-- =====================================================================
-- 022 — « The Animals » éclaté en trois thèmes
--
-- Le thème unique partait de l'article `Animal`. Cet article est écrit
-- pour définir CE QU'EST un animal : son origine (éponges, cténaires,
-- cnidaires), son plan de symétrie (Bilateria, protostomiens) et sa
-- classification. Le crawl a hérité de ce plan, et a produit 146
-- chapitres où ne figurait ni mammifère, ni oiseau, ni insecte, ni
-- poisson, ni reptile. 116 des 146 pendaient à `Taxonomy (biology)`,
-- c'est-à-dire au nom que l'homme donne aux bêtes plutôt qu'aux bêtes.
--
-- Trois thèmes le remplacent, chacun avec sa propre graine :
--
--   Marine Animals  ← Marine life        33 voisins
--   Birds           ← Bird               18 voisins
--   Land Animals    ← Terrestrial animal  4 voisins, greffes en renfort
--
-- `Terrestrial animal` est maigre — ses quatre voisins sont des limaces
-- et des escargots. Il reste la bonne RACINE (c'est le titre juste), et
-- les grands groupes terrestres viennent en greffe : Mammal, Insect,
-- Reptile, Amphibian, Arthropod, posés en branches de niveau 1.
--
-- L'ordre des positions suit les jours : les animaux de la mer et les
-- oiseaux au cinquième, les bêtes de la terre et l'homme au sixième.
-- The Human Being descend donc de 9 à 11.
--
-- Les 146 chapitres du thème 8 sont effacés À LA MAIN, avant le thème.
-- `chapter.theme_id` est pourtant en ON DELETE CASCADE — mais la cascade
-- ne se déclenche que si `PRAGMA foreign_keys` est actif, et il ne l'est
-- pas dans la connexion de `migrate.py`. Un premier essai sur copie a
-- laissé les 146 lignes orphelines, pointant un thème disparu ; c'est le
-- contrôle d'intégrité de `migrate.py` qui l'a vu et a tout restauré.
-- Ne jamais compter sur une cascade dans une migration : l'écrire.
--
-- Rien d'autre ne pend à ces chapitres : `exercise` et `exercise_prompt`
-- sont vides, personne n'a encore écrit une seule question.
-- =====================================================================

-- Faire de la place avant d'insérer : deux thèmes ne partagent pas
-- une position, et l'homme doit rester le dernier.
UPDATE theme SET position = 11 WHERE slug = 'the-human-being';

DELETE FROM chapter
 WHERE theme_id = (SELECT id FROM theme WHERE slug = 'the-animals');

DELETE FROM theme WHERE slug = 'the-animals';

INSERT INTO theme (slug, title, seed_url, color, position, status) VALUES
  ('marine-animals', 'Marine Animals',
   'https://en.wikipedia.org/wiki/Marine_life',       '#0D9488',  8, 'active'),
  ('birds',          'Birds',
   'https://en.wikipedia.org/wiki/Bird',              '#BE123C',  9, 'active'),
  ('land-animals',   'Land Animals',
   'https://en.wikipedia.org/wiki/Terrestrial_animal','#4D7C0F', 10, 'active');
