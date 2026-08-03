-- =====================================================================
-- Sara — prompt templates · English
--
-- Same 5 × 4 matrix as the French set. A theme is written in one
-- language, so its exercises must be written by a prompt in that same
-- language — never translated after the fact.
--
--   sqlite3 data/sara.db < db/seed_prompts_en.sql
-- =====================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS _common_en;
CREATE TEMP TABLE _common_en (preamble TEXT, contract TEXT, schema TEXT);

INSERT INTO _common_en VALUES (
'You write short exercises for an app where people answer with one tap.
Topic: {{title}}
Tags: {{tags}}

Here is the lesson, in Markdown. Rely on it ALONE: invent nothing, add
nothing from your general knowledge.

--- LESSON START ---
{{source}}
--- LESSON END ---
',

'
OUTPUT CONTRACT — a JSON array of {{count}} objects, nothing else.
No code fence, no text before or after.

[{
  "prompt":        "the question, 240 characters maximum",
  "body":          "null unless stated otherwise above",
  "options":       [{"label":"…","feedback":"…"}],
  "correct_index": 0,
  "ok_title":      "2 to 4 words, warm — e.g. \"Nicely done.\"",
  "ok_line":       "one sentence confirming the reasoning, 200 max",
  "ko_title":      "2 to 4 words, never blaming — e.g. \"So close.\"",
  "ko_line":       "one sentence that defuses and points the way, 200 max",
  "exp_title":     "the idea to remember, one sentence, 160 max",
  "exp_text":      "the explanation, 600 characters maximum",
  "exp_tip":       "the memorable rule, 240 maximum"
}]

RULES
- Each "label" is 60 characters maximum. Every option is plausible:
  never filler that can be dismissed at a glance.
- "feedback" explains why THAT option specifically is right or wrong.
- "correct_index" is the index of the right answer inside "options".
- Vary the position of the right answer from one exercise to the next.
- Plain, direct English. No exam-room phrasing.
- On a wrong answer: no judgement, no "incorrect", no "bad".',

'{"type":"array","items":{"type":"object",
 "required":["prompt","options","correct_index","exp_text"],
 "properties":{
   "prompt":{"type":"string","maxLength":240},
   "body":{"type":["string","null"],"maxLength":400},
   "options":{"type":"array","minItems":2,"maxItems":4,
     "items":{"type":"object","required":["label"],
       "properties":{"label":{"type":"string","maxLength":60},
                     "feedback":{"type":"string","maxLength":240}}}},
   "correct_index":{"type":"integer","minimum":0,"maximum":3},
   "ok_title":{"type":"string","maxLength":80},
   "ok_line":{"type":"string","maxLength":200},
   "ko_title":{"type":"string","maxLength":80},
   "ko_line":{"type":"string","maxLength":200},
   "exp_title":{"type":"string","maxLength":160},
   "exp_text":{"type":"string","maxLength":600},
   "exp_tip":{"type":"string","maxLength":240}}}}'
);

DROP TABLE IF EXISTS _q_en;
CREATE TEMP TABLE _q_en (type_question TEXT PRIMARY KEY, label TEXT, instruction TEXT, ord INTEGER);

INSERT INTO _q_en VALUES
('qcm', 'Multiple choice',
 'FORM — Multiple choice. Four options, exactly one correct. "body" stays null.
The three distractors match real confusions the lesson can clear up, not
absurdities.', 1),

('true_false', 'True / False',
 'FORM — True / False. Exactly two options: "True" then "False", in that
order. "body" stays null. "prompt" is a clear-cut claim — no "sometimes",
no "often", no "generally".', 2),

('complete', 'Fill in',
 'FORM — Fill in. "prompt" is a sentence with one element missing, marked
by "…". Four options, exactly one completes it correctly. "body" stays null.', 3),

('find_error', 'Spot the error',
 'FORM — Spot the error. "body" holds ONE false statement drawn from the
lesson — exactly one thing in it is wrong. "prompt" is
"Something is wrong here. Tap the faulty part." The options are the
fragments of "body" in quotes, including the faulty one.', 4),

('reorder', 'Put in order',
 'FORM — Put in order. Three options, each proposing a full sequence
written with " · " between items. Only one is in the right order; the
others swap two neighbouring items. "body" stays null.', 5);

DROP TABLE IF EXISTS _b_en;
CREATE TEMP TABLE _b_en (type_bloom TEXT PRIMARY KEY, label TEXT, angle TEXT, ord INTEGER);

INSERT INTO _b_en VALUES
('remember', 'recall',
 'LEVEL — Recall. Recognise and retrieve: a definition, a term, a date, a
value that appears verbatim in the lesson. No reasoning is asked for,
only finding the information again.', 1),

('understand', 'understanding',
 'LEVEL — Understanding. The why, not the what. Ask for the logic behind
the notion: rephrase it, explain a cause, tell two neighbouring notions
apart. Never plain retrieval.', 2),

('apply', 'application',
 'LEVEL — Application. A concrete situation, new, not covered in the
lesson, where the notion must be put to work to decide. The stem sets up
a case; answering requires applying the rule, not quoting it.', 3),

('analyze', 'analysis',
 'LEVEL — Analysis. Break down and choose. Several elements are set
against each other, something is off and must be spotted, or the fitting
method must be picked among several that work elsewhere. This is the most
demanding level: the right answer cannot be guessed without having
understood the structure.', 4);

INSERT OR IGNORE INTO prompt
  (lang, type_question, type_bloom, version, is_active, label, template, output_schema)
SELECT
  'en',
  q.type_question,
  b.type_bloom,
  1,
  1,
  q.label || ' · ' || b.label,
  c.preamble || char(10) || q.instruction || char(10) || char(10) || b.angle || char(10) || c.contract,
  c.schema
FROM _q_en q
CROSS JOIN _b_en b
CROSS JOIN _common_en c
ORDER BY q.ord, b.ord;

DROP TABLE _q_en;
DROP TABLE _b_en;
DROP TABLE _common_en;
