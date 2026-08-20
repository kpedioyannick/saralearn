-- =====================================================================
-- 008 — chapitres, et catégories en attente
--
-- Nouveau parcours de création : l'utilisateur ne dépose plus un cours,
-- il écrit un sujet — « les fonctions PHP ». Le modèle en tire une
-- présentation (titre, description, catégorie, mots-clés) et un
-- PROGRAMME de trois à cinq chapitres. Puis, chapitre par chapitre, il
-- écrit le prompt qui produira les questions.
--
-- Deux ajouts, et rien qui bouge dans l'existant.
--
--   · CHAPITRE. Le programme appartient à la connaissance, pas à la
--     taxonomie : « Déclarer une fonction » n'a de sens que dans « Les
--     fonctions en PHP ». Il ne pouvait pas se loger dans
--     `sub_category`, qui pend à `category` et que `theme` ne référence
--     qu'une fois — un thème n'a qu'un `sub_category_id`, là où un
--     programme en demande trois à cinq.
--
--   · CATÉGORIE EN ATTENTE. Le modèle CRÉE désormais les catégories.
--     Sans garde-fou, chaque essai abandonné en laisse une derrière lui,
--     et « Programmation », « Développement » et « Code » cohabitent au
--     bout d'un mois. Une catégorie naît donc en `draft` et n'entre au
--     catalogue qu'une fois retenue.
--
-- Tout s'écrit en base au fil de l'eau, en brouillon : une création
-- interrompue se reprend, et on garde la trace de ce que le modèle a
-- proposé même quand l'utilisateur le corrige.
--
-- RECONSTRUCTION — `exercise_prompt` est reconstruite pour relâcher un
-- NOT NULL. Les clés étrangères sont COUPÉES le temps de l'échange :
-- `exercise.exercise_prompt_id` est en ON DELETE SET NULL, et le
-- `DROP TABLE` de l'ancienne mettrait à NULL le lien de 465 exercices
-- vers le prompt qui les a écrits. Un PRAGMA ne se change pas dans une
-- transaction : il est posé avant le BEGIN, et rétabli après le COMMIT.
--
--   python3 scripts/migrate.py db/migrations/008_chapitres.sql
-- =====================================================================

PRAGMA foreign_keys = OFF;

BEGIN;

-- ---------------------------------------------------------------------
-- Catégories : un état, pour que le modèle puisse en proposer sans
-- polluer le catalogue.
--
-- Les six existantes sont actives — elles ont été écrites à la main et
-- sont déjà servies. Le défaut est 'active' pour cette raison ; c'est
-- l'insertion par le modèle qui posera 'draft' explicitement.
-- ---------------------------------------------------------------------

ALTER TABLE category ADD COLUMN status TEXT NOT NULL DEFAULT 'active'
       CHECK (status IN ('draft', 'active'));

-- Le catalogue lit (status, lang, position) : l'index porte la requête.
CREATE INDEX IF NOT EXISTS ix_category_status ON category (status, lang, position);

-- ---------------------------------------------------------------------
-- Chapitre — un temps du programme d'une connaissance
--
-- Porte deux choses de nature différente, et c'est voulu :
--   ce que le chapitre COUVRE     (title, description)
--   ce qui l'ÉCRIRA               (generated_prompt, type_question, example)
--
-- La seconde moitié arrive après la première : le programme est validé
-- par l'utilisateur, ensuite seulement le modèle rédige un prompt par
-- chapitre. D'où les colonnes nullables et le `status`.
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS chapter (
  id          INTEGER PRIMARY KEY,
  theme_id    INTEGER NOT NULL REFERENCES theme (id) ON DELETE CASCADE,
  position    INTEGER NOT NULL DEFAULT 0,

  title       TEXT    NOT NULL,
  description TEXT,

  -- Le prompt écrit PAR le modèle POUR ce chapitre. C'est lui qui
  -- deviendra le `rendered_prompt` d'un lancement, et c'est pour ça
  -- qu'on le garde tel quel : d'un exercice douteux on doit pouvoir
  -- remonter au texte exact qui l'a commandé.
  generated_prompt TEXT,

  -- Restreint aux cinq types qui existent réellement en base. `prompt`
  -- en autorise sept, mais `true_false` et `reorder` n'ont jamais rien
  -- produit et le front ne les a jamais dessinés : les proposer ici
  -- servirait des exercices que personne n'a vus fonctionner.
  type_question TEXT CHECK (type_question IN ('qcm','complete','find_error',
                                              'short_answer','cloze')),

  -- Un exercice d'exemple, en JSON, montré à l'utilisateur avant qu'il
  -- ne lance la rédaction : il voit ce qu'il obtiendra.
  example     TEXT,

  -- draft     : proposé par le modèle, pas encore retenu
  -- validated : retenu par l'utilisateur, prêt à produire
  -- rejected  : écarté ; gardé pour ne pas le reproposer
  status      TEXT NOT NULL DEFAULT 'draft'
              CHECK (status IN ('draft', 'validated', 'rejected')),

  -- Traces de la rédaction du prompt, sur le modèle d'`exercise_prompt` :
  -- un chapitre qui échoue n'emporte pas les autres, encore faut-il
  -- savoir lequel a échoué et pourquoi.
  model       TEXT,
  error       TEXT,

  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (theme_id, position)
);

CREATE INDEX IF NOT EXISTS ix_chapter_theme ON chapter (theme_id, status);

-- ---------------------------------------------------------------------
-- Rattacher les lancements au chapitre qui les a commandés
--
-- Nullable, et il doit le rester : les 151 lancements déjà en base
-- viennent de l'ancien chemin, où le prompt était un gabarit global et
-- non le prompt d'un chapitre. Les laisser à NULL dit la vérité.
-- ---------------------------------------------------------------------

-- `prompt_id` est NOT NULL : un lancement devait forcément citer un
-- gabarit. Le nouveau chemin n'en cite aucun — le texte envoyé au modèle
-- est écrit par lui, et vit dans `chapter.generated_prompt`.
--
-- SQLite ne sait pas relâcher un NOT NULL en place : il faut reconstruire.
-- La table ne fait que 151 lignes, et l'alternative — un faux gabarit
-- dont l'unique rôle serait de satisfaire la clé — laisserait dans
-- `prompt` une ligne que personne ne saurait interpréter plus tard.
--
-- L'ordre compte. On compte les lignes AVANT de supprimer l'ancienne
-- table, et le garde-fou fait échouer la transaction entière si le
-- compte ne tombe pas juste : `executescript` s'arrête à la première
-- erreur, et `migrate.py` restaure la sauvegarde.

CREATE TABLE exercise_prompt_new (
  id              INTEGER PRIMARY KEY,
  theme_id        INTEGER NOT NULL REFERENCES theme (id)    ON DELETE CASCADE,
  -- Nullable désormais : un lancement vient soit d'un gabarit versionné
  -- (ancien chemin), soit d'un chapitre (nouveau). Jamais des deux.
  prompt_id       INTEGER          REFERENCES prompt (id),
  chapter_id      INTEGER          REFERENCES chapter (id)  ON DELETE SET NULL,

  rendered_prompt TEXT    NOT NULL,
  model           TEXT,
  requested_count INTEGER NOT NULL DEFAULT 10,
  produced_count  INTEGER NOT NULL DEFAULT 0,

  status          TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','running','done','failed')),
  error           TEXT,

  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at     TEXT,

  -- Une origine, et une seule.
  CHECK (prompt_id IS NOT NULL OR chapter_id IS NOT NULL)
);

INSERT INTO exercise_prompt_new (id, theme_id, prompt_id, chapter_id,
                                 rendered_prompt, model, requested_count,
                                 produced_count, status, error,
                                 created_at, finished_at)
SELECT id, theme_id, prompt_id, NULL,
       rendered_prompt, model, requested_count,
       produced_count, status, error,
       created_at, finished_at
FROM exercise_prompt;

-- Garde-fou : si le report a perdu une ligne, on ne supprime rien.
CREATE TABLE migration_guard_008 (n INTEGER NOT NULL CHECK (n = 0));
INSERT INTO migration_guard_008 (n)
SELECT (SELECT COUNT(*) FROM exercise_prompt)
     - (SELECT COUNT(*) FROM exercise_prompt_new);

DROP TABLE exercise_prompt;
ALTER TABLE exercise_prompt_new RENAME TO exercise_prompt;

CREATE INDEX ix_exercise_prompt_theme   ON exercise_prompt (theme_id, status);
CREATE INDEX ix_exercise_prompt_prompt  ON exercise_prompt (prompt_id);
CREATE INDEX ix_exercise_prompt_chapter ON exercise_prompt (chapter_id);

DROP TABLE migration_guard_008;

COMMIT;

PRAGMA foreign_keys = ON;
PRAGMA foreign_key_check;
