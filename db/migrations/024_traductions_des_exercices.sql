-- =====================================================================
-- 024 — les traductions d'exercices
--
-- L'anglais reste la source. Un exercice n'existe qu'une fois, avec un
-- seul identifiant : c'est ce qui garde `attempt`, la progression et les
-- classements comparables d'une langue à l'autre. Traduire en fabriquant
-- un second exercice aurait coupé chaque classement de chapitre en deux,
-- et « 40 % de ce chapitre » n'aurait plus rien voulu dire.
--
-- Ce que la table NE porte PAS, et c'est le point le plus important :
-- `correct_index`. La bonne réponse est une POSITION dans le tableau
-- d'options, et cette position appartient à l'original. Si un traducteur
-- réordonne les options — ils le font — recopier l'index désignerait une
-- autre réponse et l'exercice deviendrait faux sans que rien ne le
-- signale. L'index se lit toujours dans `exercise`, jamais ici.
--
-- Pas de contrainte sur la valeur de `lang` : ajouter l'espagnol un jour
-- ne doit pas demander une migration. C'est tout l'intérêt d'une table
-- à part plutôt que de colonnes `_fr` dans `exercise`.
--
-- La clé primaire composite tient lieu d'index : la jointure du feed
-- cherche exactement (exercise_id, lang).
--
-- `source` dit QUI a traduit. Le choix du jour est `deep-translator`,
-- qui traduit chaque champ isolément ; un moteur qui verrait l'exercice
-- entier ferait mieux sur l'accord et le sens. Garder la trace permet de
-- repasser plus tard sur ce qu'un moteur donné a produit, sans toucher
-- au reste.
-- =====================================================================

CREATE TABLE exercise_translation (
  exercise_id INTEGER NOT NULL REFERENCES exercise (id) ON DELETE CASCADE,
  lang        TEXT    NOT NULL,

  prompt      TEXT    NOT NULL,
  body        TEXT,
  -- Même forme que `exercise.options` : [{"label": …, "feedback": …}],
  -- dans le MÊME ORDRE. C'est l'ordre qui porte la réponse.
  options     TEXT    NOT NULL CHECK (json_valid(options)),

  ok_title    TEXT,
  ok_line     TEXT,
  ko_title    TEXT,
  ko_line     TEXT,
  exp_title   TEXT,
  exp_text    TEXT    NOT NULL,

  source      TEXT    NOT NULL DEFAULT 'deep-translator',
  created_at  TEXT    NOT NULL DEFAULT (datetime('now')),

  PRIMARY KEY (exercise_id, lang)
);
