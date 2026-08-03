-- =====================================================================
-- Sara — jeu de démonstration
--
-- Reprend exactement le contenu de src/data/content.ts, pour que l'API
-- serve dès le premier jour ce que le front affiche déjà en dur.
-- Les exercices sont marqués 'validated' : ils sortent donc au feed.
--
--   sqlite3 data/sara.db < db/seed_demo.sql
-- =====================================================================

PRAGMA foreign_keys = ON;

DELETE FROM theme_tag;
DELETE FROM exercise;
DELETE FROM exercise_prompt;
DELETE FROM theme;
DELETE FROM sub_category;
DELETE FROM category;
DELETE FROM tag;

-- ---------------------------------------------------------------------
-- Catégories et sous-catégories
-- ---------------------------------------------------------------------

INSERT INTO category (id, slug, label, color, position) VALUES
  (1, 'langues',  'Langues',            '#1684D6', 1),
  (2, 'mythes',   'Mythes & histoire',  '#7A4FCB', 2),
  (3, 'vivant',   'Sciences du vivant', '#EC4880', 3),
  (4, 'musique',  'Musique',            '#E29412', 4),
  (5, 'ciel',     'Ciel & espace',      '#2F8A74', 5),
  (6, 'logique',  'Logique',            '#4E3A91', 6);

INSERT INTO sub_category (id, category_id, slug, label, color, position) VALUES
  (1, 1, 'vocabulaire-anglais', 'Vocabulaire anglais', '#1684D6', 1),
  (2, 1, 'faux-amis',           'Faux amis',           '#1684D6', 2),
  (3, 2, 'mythologie-grecque',  'Mythologie grecque',  '#7A4FCB', 1),
  (4, 2, 'rome-antique',        'Rome antique',        '#7A4FCB', 2),
  (5, 3, 'corps-humain',        'Corps humain',        '#EC4880', 1),
  (6, 3, 'cellules-adn',        'Cellules & ADN',      '#EC4880', 2),
  (7, 4, 'accords-guitare',     'Accords de guitare',  '#E29412', 1),
  (8, 5, 'systeme-solaire',     'Système solaire',     '#2F8A74', 1);

-- ---------------------------------------------------------------------
-- Thèmes — publics, sans source Markdown (contenu écrit à la main)
-- ---------------------------------------------------------------------

INSERT INTO theme (id, category_id, sub_category_id, slug, title, color, visibility, published_at) VALUES
  (1, 1, 1, 'vocabulaire-anglais', 'Vocabulaire anglais', '#1684D6', 'public', datetime('now')),
  (2, 2, 3, 'mythologie-grecque',  'Mythologie grecque',  '#7A4FCB', 'public', datetime('now')),
  (3, 3, 5, 'corps-humain',        'Corps humain',        '#EC4880', 'public', datetime('now')),
  (4, 4, 7, 'accords-guitare',     'Accords de guitare',  '#E29412', 'public', datetime('now')),
  (5, 5, 8, 'systeme-solaire',     'Système solaire',     '#2F8A74', 'public', datetime('now'));

INSERT INTO tag (id, slug, label) VALUES
  (1, 'latin', 'latin'), (2, 'registre-soutenu', 'registre soutenu'),
  (3, 'ovide', 'Ovide'), (4, 'circulation', 'circulation'),
  (5, 'tierces', 'tierces'), (6, 'harmonie', 'harmonie'),
  (7, 'telluriques', 'planètes telluriques');

INSERT INTO theme_tag (theme_id, tag_id) VALUES
  (1,1),(1,2),(2,3),(3,4),(4,5),(4,6),(5,7);

-- ---------------------------------------------------------------------
-- Exercices — les cinq de la maquette, un par type de question
-- ---------------------------------------------------------------------

INSERT INTO exercise
  (theme_id, type_question, type_bloom, prompt, body, options, correct_index,
   ok_title, ok_line, ko_title, ko_line, exp_title, exp_text, exp_tip, state)
VALUES
(1, 'qcm', 'remember',
 '« Ubiquitous » se traduit le mieux par :', NULL,
 json('[{"label":"Ambigu","feedback":"Ambigu se dit ambiguous — proche à l''œil, mais sans rapport de sens."},
        {"label":"Omniprésent","feedback":"Oui : ce qui se trouve partout à la fois."},
        {"label":"Superflu","feedback":"Superflu se dit superfluous ; la ressemblance sonore trompe."},
        {"label":"Éphémère","feedback":"Éphémère, c''est ephemeral — presque l''inverse."}]'),
 1,
 'Bien vu.', 'C''est exactement le sens le plus courant du mot.',
 'Presque.', 'Le mot piège tout le monde la première fois.',
 'Ubiquitous, c''est « qui est partout à la fois ».',
 'Le mot vient du latin ubique, « partout ». On le trouve surtout dans les registres soutenus : ubiquitous smartphones, ubiquitous surveillance.',
 'ubique = partout → ubiquitous = omniprésent.',
 'validated'),

(2, 'true_false', 'understand',
 'Icare meurt en tombant dans la mer après s''être trop approché du soleil.', NULL,
 json('[{"label":"Vrai","feedback":"Oui, c''est bien le récit que rapporte Ovide."},
        {"label":"Faux","feedback":"Le récit existe bien ainsi — c''est Dédale, le père, qui survit."}]'),
 0,
 'Exact.', 'La chute d''Icare, telle que la raconte Ovide.',
 'Pas tout à fait.', 'L''histoire est souvent confondue avec celle de Dédale.',
 'La cire des ailes fond, Icare tombe.',
 'Dédale fabrique deux paires d''ailes en plumes et cire pour fuir le labyrinthe. Il prévient son fils : ni trop haut, ni trop bas. Icare monte, la cire fond, il tombe dans la mer qui portera son nom.',
 'Le récit met en garde contre l''excès, pas contre le vol.',
 'validated'),

(3, 'complete', 'remember',
 'Le sang oxygéné quitte le cœur par l''artère …', NULL,
 json('[{"label":"aorte","feedback":"Oui : elle part du ventricule gauche vers tout le corps."},
        {"label":"carotide","feedback":"La carotide irrigue la tête, mais elle naît de l''aorte."},
        {"label":"pulmonaire","feedback":"Elle part du ventricule droit, et transporte du sang pauvre en oxygène."},
        {"label":"veine cave","feedback":"C''est une veine, et elle ramène le sang au cœur."}]'),
 0,
 'Juste.', 'Le plus gros vaisseau du corps.',
 'Presque.', 'Tous ces vaisseaux existent — un seul part du ventricule gauche.',
 'L''aorte part du ventricule gauche.',
 'Elle distribue le sang oxygéné à tout le corps. L''artère pulmonaire, elle, part du ventricule droit et va vers les poumons : c''est la seule artère qui transporte du sang pauvre en oxygène.',
 'Ventricule gauche → aorte → corps. Ventricule droit → artère pulmonaire → poumons.',
 'validated'),

(4, 'find_error', 'analyze',
 'Une erreur s''est glissée. Touche l''élément fautif.',
 'Un accord de Do majeur se compose de Do, Mi bémol et Sol.',
 json('[{"label":"« accord »","feedback":"Le terme est correct : trois notes jouées ensemble."},
        {"label":"« Do »","feedback":"Do est bien la fondamentale de l''accord de Do."},
        {"label":"« Mi bémol »","feedback":"C''est là : avec Mi bémol la tierce devient mineure."},
        {"label":"« Sol »","feedback":"Sol est bien la quinte juste de Do."}]'),
 2,
 'Bien repéré.', 'C''est bien la tierce qui était fausse.',
 'Ce n''était pas là.', 'Regarde du côté de la tierce.',
 'Do majeur, c''est Do – Mi – Sol.',
 'Un accord majeur empile une tierce majeure puis une tierce mineure. Avec Mi bémol, la tierce devient mineure : on obtient Do mineur, un accord bien plus sombre.',
 'Tierce majeure = majeur. Tierce bémolisée = mineur.',
 'validated'),

(5, 'reorder', 'apply',
 'Du plus proche au plus loin du Soleil :', NULL,
 json('[{"label":"Mercure · Vénus · Mars · Terre","feedback":"Mars et la Terre sont inversées."},
        {"label":"Mercure · Vénus · Terre · Mars","feedback":"Oui : les quatre telluriques dans l''ordre."},
        {"label":"Vénus · Mercure · Terre · Mars","feedback":"Mercure est la plus proche du Soleil, avant Vénus."}]'),
 1,
 'Parfait.', 'Les quatre planètes telluriques dans l''ordre.',
 'Deux planètes sont inversées.', 'La Terre est notre troisième repère.',
 'Mercure, Vénus, Terre, Mars.',
 'Ce sont les quatre planètes rocheuses, avant la ceinture d''astéroïdes. Vénus est plus chaude que Mercure malgré sa distance, à cause de son atmosphère épaisse.',
 'Mercure · Vénus · Terre · Mars, puis la ceinture d''astéroïdes.',
 'validated');

-- Compteur dénormalisé, recalculé depuis la source.
UPDATE theme SET exercise_count = (
  SELECT COUNT(*) FROM exercise e WHERE e.theme_id = theme.id AND e.state = 'validated'
);
