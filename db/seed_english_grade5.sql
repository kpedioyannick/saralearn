-- =====================================================================
-- English — Grade 5 (équivalent CM2)
--
-- PROVENANCE : ces notions reprennent les standards « Language » du
-- Common Core pour le Grade 5 (L.5.1 à L.5.6). Contrairement au
-- catalogue de panneaux, elles ne sont PAS extraites d'une source
-- machine : le PDF officiel présente trois niveaux en colonnes et
-- résiste à l'extraction. Elles sont écrites de mémoire du référentiel.
--
--   → À RELIRE contre thecorestandards.org/ELA-Literacy/L/5/ avant de
--     considérer le contenu comme fiable. Le code L.5.x de chaque
--     notion est laissé en clair pour rendre cette relecture rapide.
--
-- POURQUOI PAS DE « CONJUGAISON » : le programme américain n'en a pas.
-- Le verbe anglais est trop simple pour justifier une discipline — les
-- temps se traitent à l'intérieur de la grammaire. La taxonomie
-- anglaise n'est donc pas le miroir de la française, d'où la colonne
-- `lang` sur sub_category (migration 005).
--
--   sqlite3 data/sara.db < db/seed_english_grade5.sql
-- =====================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO category (slug, label, label_en, color, position, lang)
  VALUES ('english', 'English', 'English', '#1684D6', 2, 'en');

INSERT OR IGNORE INTO sub_category (category_id, slug, label, label_en, color, position, lang)
  SELECT id, 'grammar', 'Grammar', 'Grammar', '#1684D6', 1, 'en' FROM category WHERE slug='english';
INSERT OR IGNORE INTO sub_category (category_id, slug, label, label_en, color, position, lang)
  SELECT id, 'spelling', 'Spelling', 'Spelling', '#1684D6', 2, 'en' FROM category WHERE slug='english';
INSERT OR IGNORE INTO sub_category (category_id, slug, label, label_en, color, position, lang)
  SELECT id, 'vocabulary', 'Vocabulary', 'Vocabulary', '#1684D6', 3, 'en' FROM category WHERE slug='english';

INSERT OR IGNORE INTO tag (slug, label) VALUES ('grade-5', 'Grade 5');

-- ---------------------------------------------------------------------
-- Grammar — L.5.1 (conventions of standard English) et L.5.3a
-- ---------------------------------------------------------------------

INSERT OR IGNORE INTO theme (category_id, sub_category_id, slug, title, description,
                             color, source_markdown, lang, country, visibility, published_at)
SELECT c.id, s.id, v.slug, v.title, v.descr, '#1684D6', v.md, 'en', 'US', 'public', datetime('now')
FROM category c JOIN sub_category s ON s.category_id = c.id
CROSS JOIN (
  SELECT 'en-g5-conjunctions' AS slug,
         'Conjunctions, prepositions and interjections' AS title,
         'Common Core L.5.1a — Grade 5.' AS descr,
         '# Conjunctions, prepositions and interjections

Level: Grade 5 · Common Core L.5.1a

## What the learner should be able to do

- Explain the function of conjunctions, prepositions and interjections in general.
- Explain what each of them does in a particular sentence.
- Tell a coordinating conjunction (and, but, or, so) from a subordinating one (because, although, while).
- Recognise a prepositional phrase and what it modifies.' AS md
  UNION ALL SELECT 'en-g5-perfect-tenses', 'Perfect verb tenses', 'Common Core L.5.1b — Grade 5.',
  '# Perfect verb tenses

Level: Grade 5 · Common Core L.5.1b

## What the learner should be able to do

- Form the perfect tenses: I had walked, I have walked, I will have walked.
- Use the past perfect for an action completed before another past action.
- Use the present perfect for an action linked to the present.
- Choose between simple past and present perfect in context.'
  UNION ALL SELECT 'en-g5-verb-tense-meaning', 'Using verb tense to convey time and sequence', 'Common Core L.5.1c — Grade 5.',
  '# Using verb tense to convey time and sequence

Level: Grade 5 · Common Core L.5.1c

## What the learner should be able to do

- Use verb tense to show various times, sequences, states and conditions.
- Order two events correctly using tense alone.
- Match the tense to the time expression in the sentence (yesterday, by then, since).'
  UNION ALL SELECT 'en-g5-tense-shifts', 'Inappropriate shifts in verb tense', 'Common Core L.5.1d — Grade 5.',
  '# Inappropriate shifts in verb tense

Level: Grade 5 · Common Core L.5.1d

## What the learner should be able to do

- Recognise an unwarranted change of tense inside a sentence or a paragraph.
- Correct the shift so the passage keeps one consistent time frame.
- Tell a deliberate change of time from a mistake.'
  UNION ALL SELECT 'en-g5-correlative', 'Correlative conjunctions', 'Common Core L.5.1e — Grade 5.',
  '# Correlative conjunctions

Level: Grade 5 · Common Core L.5.1e

## What the learner should be able to do

- Use correlative conjunctions in pairs: either/or, neither/nor, both/and, not only/but also.
- Keep the two halves of the pair parallel in structure.
- Spot a broken pair (either … nor) and repair it.'
  UNION ALL SELECT 'en-g5-sentence-work', 'Expanding, combining and reducing sentences', 'Common Core L.5.3a — Grade 5.',
  '# Expanding, combining and reducing sentences

Level: Grade 5 · Common Core L.5.3a

## What the learner should be able to do

- Combine two short sentences into one without changing the meaning.
- Expand a sentence by adding detail in the right place.
- Reduce a wordy sentence while keeping what matters.'
) v
WHERE c.slug='english' AND s.slug='grammar';

-- ---------------------------------------------------------------------
-- Spelling — L.5.2 (capitalisation, punctuation, spelling)
--
-- Rappel : « spelling » est LEXICAL. Il n'a pas d'équivalent de
-- l'orthographe grammaticale française — un adjectif anglais ne
-- s'accorde pas, un verbe ne change pas selon le sujet.
-- ---------------------------------------------------------------------

INSERT OR IGNORE INTO theme (category_id, sub_category_id, slug, title, description,
                             color, source_markdown, lang, country, visibility, published_at)
SELECT c.id, s.id, v.slug, v.title, v.descr, '#1684D6', v.md, 'en', 'US', 'public', datetime('now')
FROM category c JOIN sub_category s ON s.category_id = c.id
CROSS JOIN (
  SELECT 'en-g5-series-punctuation' AS slug, 'Punctuating items in a series' AS title,
         'Common Core L.5.2a — Grade 5.' AS descr,
  '# Punctuating items in a series

Level: Grade 5 · Common Core L.5.2a

## What the learner should be able to do

- Separate three or more items in a series with commas.
- Place the comma before the final conjunction where the style requires it.
- Punctuate a series of phrases, not only of single words.' AS md
  UNION ALL SELECT 'en-g5-introductory-comma', 'Commas after an introductory element', 'Common Core L.5.2b — Grade 5.',
  '# Commas after an introductory element

Level: Grade 5 · Common Core L.5.2b

## What the learner should be able to do

- Use a comma to separate an introductory word, phrase or clause from the rest of the sentence.
- Recognise when the opening element is short enough to need no comma.'
  UNION ALL SELECT 'en-g5-comma-address', 'Commas with yes, no, tag questions and direct address', 'Common Core L.5.2c — Grade 5.',
  '# Commas with yes, no, tag questions and direct address

Level: Grade 5 · Common Core L.5.2c

## What the learner should be able to do

- Set off yes and no with a comma.
- Set off a tag question: You are coming, aren''t you?
- Set off the name of the person addressed: Maria, please close the door.'
  UNION ALL SELECT 'en-g5-titles', 'Marking titles of works', 'Common Core L.5.2d — Grade 5.',
  '# Marking titles of works

Level: Grade 5 · Common Core L.5.2d

## What the learner should be able to do

- Use italics or underlining for the titles of long works: books, films, newspapers.
- Use quotation marks for the titles of short works: poems, songs, articles, chapters.'
  UNION ALL SELECT 'en-g5-spelling-words', 'Spelling grade-appropriate words', 'Common Core L.5.2e — Grade 5.',
  '# Spelling grade-appropriate words

Level: Grade 5 · Common Core L.5.2e

## What the learner should be able to do

- Apply the doubling rule: run → running, but hope → hoping.
- Drop the silent e before a vowel suffix: make → making.
- Change y to i: happy → happiness, carry → carried.
- Spell frequently confused words correctly: their/there/they''re, its/it''s, your/you''re.
- Consult a dictionary when unsure.'
) v
WHERE c.slug='english' AND s.slug='spelling';

-- ---------------------------------------------------------------------
-- Vocabulary — L.5.4, L.5.5, L.5.6
-- ---------------------------------------------------------------------

INSERT OR IGNORE INTO theme (category_id, sub_category_id, slug, title, description,
                             color, source_markdown, lang, country, visibility, published_at)
SELECT c.id, s.id, v.slug, v.title, v.descr, '#1684D6', v.md, 'en', 'US', 'public', datetime('now')
FROM category c JOIN sub_category s ON s.category_id = c.id
CROSS JOIN (
  SELECT 'en-g5-context-clues' AS slug, 'Using context clues' AS title,
         'Common Core L.5.4a — Grade 5.' AS descr,
  '# Using context clues

Level: Grade 5 · Common Core L.5.4a

## What the learner should be able to do

- Use the surrounding sentence or paragraph to work out what an unknown word means.
- Recognise a definition, an example or a contrast used as a clue.' AS md
  UNION ALL SELECT 'en-g5-roots-affixes', 'Greek and Latin roots and affixes', 'Common Core L.5.4b — Grade 5.',
  '# Greek and Latin roots and affixes

Level: Grade 5 · Common Core L.5.4b

## What the learner should be able to do

- Use common roots as clues to meaning: photo, graph, port, dict, struct, scrib.
- Use common prefixes: un-, re-, pre-, dis-, mis-, non-.
- Use common suffixes: -less, -ful, -tion, -able, -ist, -ology.'
  UNION ALL SELECT 'en-g5-reference', 'Using reference materials', 'Common Core L.5.4c — Grade 5.',
  '# Using reference materials

Level: Grade 5 · Common Core L.5.4c

## What the learner should be able to do

- Find a word in a dictionary, print or digital.
- Read a dictionary entry: pronunciation, part of speech, several senses.
- Choose the sense that fits the sentence at hand.'
  UNION ALL SELECT 'en-g5-figurative', 'Similes and metaphors', 'Common Core L.5.5a — Grade 5.',
  '# Similes and metaphors

Level: Grade 5 · Common Core L.5.5a

## What the learner should be able to do

- Tell a simile (as brave as a lion) from a metaphor (he is a lion).
- Explain what a figure of speech means in its context.'
  UNION ALL SELECT 'en-g5-idioms', 'Idioms, adages and proverbs', 'Common Core L.5.5b — Grade 5.',
  '# Idioms, adages and proverbs

Level: Grade 5 · Common Core L.5.5b

## What the learner should be able to do

- Recognise a common idiom and give its meaning: break the ice, once in a blue moon.
- Explain a familiar adage or proverb: better late than never.
- See that the meaning is not the sum of the words.'
  UNION ALL SELECT 'en-g5-word-relationships', 'Synonyms, antonyms and homographs', 'Common Core L.5.5c — Grade 5.',
  '# Synonyms, antonyms and homographs

Level: Grade 5 · Common Core L.5.5c

## What the learner should be able to do

- Use the relationship between words to understand each of them better.
- Find a synonym and an antonym for a given word.
- Tell apart homographs — words spelled alike with different meanings: bass, tear, lead.'
  UNION ALL SELECT 'en-g5-academic-vocabulary', 'Academic and domain-specific words', 'Common Core L.5.6 — Grade 5.',
  '# Academic and domain-specific words

Level: Grade 5 · Common Core L.5.6

## What the learner should be able to do

- Use grade-appropriate academic words accurately: however, therefore, consequently, compare.
- Use domain-specific words from science, history and mathematics in the right context.'
) v
WHERE c.slug='english' AND s.slug='vocabulary';

-- Tag de niveau sur tout ce qui vient d'être créé.
INSERT OR IGNORE INTO theme_tag (theme_id, tag_id)
SELECT t.id, (SELECT id FROM tag WHERE slug='grade-5')
FROM theme t WHERE t.slug LIKE 'en-g5-%';
