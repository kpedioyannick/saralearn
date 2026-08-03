-- =====================================================================
-- Sara — English demo content
--
-- A theme is written in one language, so English users need their own
-- themes and exercises — never a translation of the French ones.
--
--   sqlite3 data/sara.db < db/seed_demo_en.sql
-- =====================================================================

PRAGMA foreign_keys = ON;

DELETE FROM exercise WHERE theme_id IN (SELECT id FROM theme WHERE lang = 'en');
DELETE FROM theme WHERE lang = 'en';

INSERT INTO theme (id, category_id, sub_category_id, slug, title, color, lang, visibility, published_at) VALUES
  (101, 2, 3, 'greek-mythology-en', 'Greek mythology', '#7A4FCB', 'en', 'public', datetime('now')),
  (102, 3, 5, 'human-body-en',      'Human body',      '#EC4880', 'en', 'public', datetime('now')),
  (103, 5, 8, 'solar-system-en',    'Solar system',    '#2F8A74', 'en', 'public', datetime('now')),
  (104, 4, 7, 'guitar-chords-en',   'Guitar chords',   '#E29412', 'en', 'public', datetime('now'));

INSERT INTO exercise
  (theme_id, type_question, type_bloom, prompt, body, options, correct_index,
   ok_title, ok_line, ko_title, ko_line, exp_title, exp_text, exp_tip, state)
VALUES
(101, 'true_false', 'understand',
 'Icarus dies falling into the sea after flying too close to the sun.', NULL,
 json('[{"label":"True","feedback":"Yes — that is the story as Ovid tells it."},
        {"label":"False","feedback":"The story does run that way. It is Daedalus, the father, who survives."}]'),
 0,
 'Exactly.', 'The fall of Icarus, as Ovid tells it.',
 'Not quite.', 'This one often gets mixed up with the story of Daedalus.',
 'The wax melts, and Icarus falls.',
 'Daedalus builds two pairs of wings from feathers and wax to escape the labyrinth. He warns his son: not too high, not too low. Icarus climbs, the wax melts, and he falls into the sea that would carry his name.',
 'The story warns against excess, not against flight.',
 'validated'),

(102, 'complete', 'remember',
 'Oxygenated blood leaves the heart through the … artery.', NULL,
 json('[{"label":"aorta","feedback":"Yes — it leaves the left ventricle and feeds the whole body."},
        {"label":"carotid","feedback":"The carotid supplies the head, but it branches off the aorta."},
        {"label":"pulmonary","feedback":"That one leaves the right ventricle, carrying oxygen-poor blood."},
        {"label":"vena cava","feedback":"That is a vein, and it brings blood back to the heart."}]'),
 0,
 'Right.', 'The largest vessel in the body.',
 'So close.', 'All of these exist — only one leaves the left ventricle.',
 'The aorta leaves the left ventricle.',
 'It distributes oxygenated blood to the whole body. The pulmonary artery, by contrast, leaves the right ventricle for the lungs: it is the only artery carrying oxygen-poor blood.',
 'Left ventricle → aorta → body. Right ventricle → pulmonary artery → lungs.',
 'validated'),

(103, 'reorder', 'apply',
 'From closest to furthest from the Sun:', NULL,
 json('[{"label":"Mercury · Venus · Mars · Earth","feedback":"Mars and Earth are swapped."},
        {"label":"Mercury · Venus · Earth · Mars","feedback":"Yes — the four rocky planets in order."},
        {"label":"Venus · Mercury · Earth · Mars","feedback":"Mercury is the closest to the Sun, ahead of Venus."}]'),
 1,
 'Perfect.', 'The four terrestrial planets, in order.',
 'Two planets are swapped.', 'Earth is our third marker.',
 'Mercury, Venus, Earth, Mars.',
 'These are the four rocky planets, sitting before the asteroid belt. Venus is hotter than Mercury despite being further out, because of its thick atmosphere.',
 'Mercury · Venus · Earth · Mars, then the asteroid belt.',
 'validated'),

(104, 'find_error', 'analyze',
 'Something is wrong here. Tap the faulty part.',
 'A C major chord is made of C, E flat and G.',
 json('[{"label":"\"chord\"","feedback":"The term is right: three notes played together."},
        {"label":"\"C\"","feedback":"C is indeed the root of a C chord."},
        {"label":"\"E flat\"","feedback":"There it is: with E flat the third becomes minor."},
        {"label":"\"G\"","feedback":"G is the perfect fifth of C."}]'),
 2,
 'Well spotted.', 'The third was the faulty one.',
 'Not there.', 'Look at the third.',
 'C major is C – E – G.',
 'A major chord stacks a major third then a minor third. With E flat the third turns minor, and you get C minor — a far darker chord.',
 'Major third = major. Flattened third = minor.',
 'validated');

UPDATE theme SET exercise_count = (
  SELECT COUNT(*) FROM exercise e WHERE e.theme_id = theme.id AND e.state = 'validated'
);
