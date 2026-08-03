-- =====================================================================
-- Sara — gabarits de prompt · SQLite
--
-- 5 types de question × 4 niveaux de Bloom = 20 gabarits, composés par
-- produit cartésien plutôt que recopiés vingt fois : le contrat de
-- sortie et les contraintes de longueur ne vivent qu'à un seul endroit.
--
-- Substitutions attendues côté service : {{title}} {{tags}} {{count}} {{source}}
--
--   sqlite3 data/sara.db < db/seed_prompts.sql
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Parties communes
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS _common;
CREATE TEMP TABLE _common (preamble TEXT, contract TEXT, schema TEXT);

INSERT INTO _common VALUES (
'Tu écris des exercices courts pour une app où l''on répond en un tap.
Thème : {{title}}
Tags : {{tags}}

Voici le cours, en Markdown. Tu ne t''appuies QUE sur lui : rien d''inventé,
rien d''ajouté depuis tes connaissances générales.

--- DÉBUT DU COURS ---
{{source}}
--- FIN DU COURS ---
',

-- Les limites ne sont pas décoratives : la règle « un écran, pas de
-- scroll » se tient à l''écriture, pas dans l''interface.
'
CONTRAT DE SORTIE — un tableau JSON de {{count}} objets, rien d''autre.
Pas de balise de code, pas de texte avant ou après.

[{
  "prompt":        "la question, 240 caractères maximum",
  "body":          "null, sauf indication contraire ci-dessus",
  "options":       [{"label":"…","feedback":"…"}],
  "correct_index": 0,
  "ok_title":      "2 à 4 mots, ton chaleureux — ex. « Bien vu. »",
  "ok_line":       "une phrase qui confirme le raisonnement, 200 max",
  "ko_title":      "2 à 4 mots, jamais culpabilisants — ex. « Presque. »",
  "ko_line":       "une phrase qui dédramatise et oriente, 200 max",
  "exp_title":     "l''idée à retenir en une phrase, 160 max",
  "exp_text":      "l''explication, 600 caractères maximum",
  "exp_tip":       "la règle mémorisable, 240 maximum"
}]

RÈGLES
- Chaque "label" fait 60 caractères maximum. Chaque option est plausible :
  jamais de remplissage évident.
- "feedback" explique pourquoi CETTE option précise est juste ou fausse.
- "correct_index" est l''indice de la bonne réponse dans "options".
- Varie la position de la bonne réponse d''un exercice à l''autre.
- Ton tutoyant, français courant, aucune formule scolaire.
- Sur l''erreur : aucun jugement, aucun « faux », aucun « mauvais ».',

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

-- ---------------------------------------------------------------------
-- Les cinq types de question
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS _q;
CREATE TEMP TABLE _q (type_question TEXT PRIMARY KEY, label TEXT, instruction TEXT);

INSERT INTO _q VALUES
('qcm', 'QCM',
 'FORME — QCM. Quatre options, une seule correcte. "body" reste null.
Les trois distracteurs correspondent à des confusions réelles que le cours
permet de lever, pas à des absurdités.'),

('true_false', 'Vrai / Faux',
 'FORME — Vrai / Faux. Exactement deux options : "Vrai" puis "Faux",
dans cet ordre. "body" reste null. "prompt" est une affirmation
tranchée — ni « parfois », ni « souvent », ni « en général ».'),

('complete', 'Complète',
 'FORME — Complète. "prompt" est une phrase dont il manque un élément,
marqué par « … ». Quatre options, une seule complète correctement.
"body" reste null.'),

('find_error', 'Trouve l''erreur',
 'FORME — Trouve l''erreur. "body" contient UNE affirmation fausse tirée
du cours — une seule chose y est incorrecte. "prompt" vaut
« Une erreur s''est glissée. Touche l''élément fautif. » Les options sont
les fragments de "body" entre guillemets français, dont le fautif.'),

('reorder', 'Remets dans l''ordre',
 'FORME — Remets dans l''ordre. Trois options, chacune proposant une
séquence complète écrite avec « · » entre les éléments. Une seule est
dans le bon ordre ; les autres intervertissent deux éléments voisins.
"body" reste null.');

-- ---------------------------------------------------------------------
-- Les quatre niveaux de Bloom
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS _b;
CREATE TEMP TABLE _b (type_bloom TEXT PRIMARY KEY, label TEXT, angle TEXT, ord INTEGER);

INSERT INTO _b VALUES
('remember', 'rappel',
 'NIVEAU — Rappel. Reconnaître et restituer : une définition, un terme,
une date, une valeur qui figure telle quelle dans le cours. On ne demande
aucun raisonnement, seulement de retrouver l''information.', 1),

('understand', 'compréhension',
 'NIVEAU — Compréhension. Le pourquoi, pas le quoi. On demande la logique
derrière la notion : reformuler, expliquer une cause, distinguer deux
notions voisines. Jamais une simple restitution.', 2),

('apply', 'application',
 'NIVEAU — Application. Une situation concrète, nouvelle, non traitée dans
le cours, où la notion doit être mise en pratique pour trancher. L''énoncé
pose un cas ; la réponse exige d''appliquer la règle, pas de la citer.', 3),

('analyze', 'analyse',
 'NIVEAU — Analyse. Décomposer et choisir. On confronte plusieurs éléments,
on repère ce qui cloche, ou on sélectionne la méthode adaptée parmi
plusieurs valables ailleurs. C''est le niveau le plus exigeant : la bonne
réponse ne se devine pas sans avoir compris la structure.', 4);

-- ---------------------------------------------------------------------
-- Produit cartésien
--
-- Rejouable : on efface les gabarits v1 qui n'ont encore rien produit,
-- et on garde ceux qui ont déjà généré des exercices — sinon on perdrait
-- la trace de ce qui a écrit quoi.
-- ---------------------------------------------------------------------

DELETE FROM prompt
WHERE version = 1
  AND id NOT IN (SELECT prompt_id FROM exercise_prompt);

INSERT OR IGNORE INTO prompt
  (type_question, type_bloom, version, is_active, label, template, output_schema)
SELECT
  q.type_question,
  b.type_bloom,
  1,
  1,
  q.label || ' · ' || b.label,
  c.preamble || char(10) || q.instruction || char(10) || char(10) || b.angle || char(10) || c.contract,
  c.schema
FROM _q q
CROSS JOIN _b b
CROSS JOIN _common c
ORDER BY q.rowid, b.ord;

DROP TABLE _q;
DROP TABLE _b;
DROP TABLE _common;
