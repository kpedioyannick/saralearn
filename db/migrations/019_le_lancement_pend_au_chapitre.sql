-- =====================================================================
-- 019 — un lancement pend à son chapitre, et à rien d'autre
--
-- `exercise_prompt` portait DEUX rattachements : `theme_id`, obligatoire
-- depuis toujours, et `chapter_id`, ajouté par la 011 et resté nul sur
-- les 202 lignes jusqu'à ce que
-- `scripts/rattacher_lancements_aux_chapitres.py` le remplisse.
--
-- Une fois les deux renseignés, la redondance saute aux yeux : sur les
-- 202 lancements, `exercise_prompt.theme_id` est égal au `theme_id` de
-- son chapitre — 202 fois sur 202. L'information est écrite deux fois.
--
-- Ce n'est pas une élégance de schéma, c'est une question de vérité.
-- Déplacer un jour un chapitre d'un thème à un autre laisserait ses
-- lancements pointer l'ancien thème, et rien ne dirait lequel des deux
-- a raison. Une donnée écrite deux fois finit par se contredire.
--
-- `theme_id` disparaît donc, et `chapter_id` devient NOT NULL. Le thème
-- reste accessible, par le chapitre :
--
--     SELECT p.* FROM exercise_prompt p
--       JOIN chapter ch ON ch.id = p.chapter_id
--      WHERE ch.theme_id = ?
--
-- LA RÈGLE DE SUPPRESSION CHANGE, ET C'EST VOULU
--
--   `chapter_id` était en ON DELETE SET NULL. Sur une colonne NOT NULL
--   c'est une contradiction : SQLite tenterait d'écrire NULL et
--   refuserait. Elle passe en CASCADE — effacer un chapitre efface ses
--   lancements.
--
--   Les exercices, eux, survivent : `exercise.exercise_prompt_id` reste
--   en SET NULL. Effacer un chapitre coupe le fil, il ne détruit pas les
--   questions écrites. C'est le comportement qu'on veut : le texte d'un
--   exercice vaut plus que la trace de sa commande.
--
--   La chaîne depuis le thème est préservée sans `theme_id` :
--   theme → chapter est en CASCADE, chapter → exercise_prompt le devient.
--   Supprimer un thème emporte toujours ses lancements, en deux sauts au
--   lieu d'un.
--
-- CE QUI EST VÉRIFIÉ AVANT L'ÉCHANGE
--
--   Qu'aucune ligne n'ait `chapter_id` nul — sinon la colonne NOT NULL
--   la refuserait et on perdrait le lancement. Et que le compte tombe
--   juste des deux côtés.
--
--   python3 scripts/migrate.py db/migrations/019_le_lancement_pend_au_chapitre.sql
-- =====================================================================

BEGIN;

CREATE TABLE exercise_prompt_neuf (
  id              INTEGER PRIMARY KEY,

  -- L'unique rattachement. NOT NULL : un lancement sans chapitre n'a
  -- plus de place dans le modèle, c'est le trou que la 019 ferme.
  chapter_id      INTEGER NOT NULL REFERENCES chapter (id) ON DELETE CASCADE,

  -- Un lancement peut en porter d'autres : une recharge de feed se
  -- déclare enfant du lancement dont elle rejoue la consigne.
  parent_id       INTEGER          REFERENCES exercise_prompt_neuf (id) ON DELETE CASCADE,

  rendered_prompt TEXT    NOT NULL,
  model           TEXT,
  requested_count INTEGER NOT NULL DEFAULT 10,
  produced_count  INTEGER NOT NULL DEFAULT 0,

  status          TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','running','done','failed')),
  error           TEXT,

  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at     TEXT,

  CHECK (parent_id IS NULL OR parent_id <> id)
);

INSERT INTO exercise_prompt_neuf (
  id, chapter_id, parent_id,
  rendered_prompt, model, requested_count, produced_count,
  status, error, created_at, finished_at)
SELECT
  id, chapter_id, parent_id,
  rendered_prompt, model, requested_count, produced_count,
  status, error, created_at, finished_at
FROM exercise_prompt;

-- ---------------------------------------------------------------------
-- Contrôle AVANT tout DROP
--
-- `RAISE(ABORT, ...)` n'existe que dans un trigger : pour échouer au
-- milieu d'un script, on viole une contrainte. Cette table n'accepte que
-- la valeur 1.
-- ---------------------------------------------------------------------

CREATE TEMP TABLE _controle_019 (
  test TEXT    NOT NULL,
  ok   INTEGER NOT NULL CHECK (ok = 1)
);

INSERT INTO _controle_019 (test, ok)
SELECT 'aucun lancement n''avait de chapitre nul',
       (SELECT COUNT(*) FROM exercise_prompt WHERE chapter_id IS NULL) = 0;

INSERT INTO _controle_019 (test, ok)
SELECT 'les 202 lancements ont été versés',
       (SELECT COUNT(*) FROM exercise_prompt_neuf) = (SELECT COUNT(*) FROM exercise_prompt);

INSERT INTO _controle_019 (test, ok)
SELECT 'aucun champ n''a glissé de colonne',
       (SELECT COUNT(*) FROM exercise_prompt a JOIN exercise_prompt_neuf b USING (id)
         WHERE a.chapter_id IS b.chapter_id
           AND a.parent_id IS b.parent_id
           AND a.rendered_prompt IS b.rendered_prompt
           AND a.model IS b.model
           AND a.produced_count IS b.produced_count
           AND a.status IS b.status
           AND a.created_at IS b.created_at)
       = (SELECT COUNT(*) FROM exercise_prompt);

-- Le thème reste atteignable par le chapitre pour tous les lancements :
-- c'est ce qui justifie de retirer `theme_id`, il faut le prouver ici.
INSERT INTO _controle_019 (test, ok)
SELECT 'chaque lancement retrouve son thème via son chapitre',
       (SELECT COUNT(*) FROM exercise_prompt_neuf p
          JOIN chapter ch ON ch.id = p.chapter_id
          JOIN theme t ON t.id = ch.theme_id)
       = (SELECT COUNT(*) FROM exercise_prompt);

-- Et il doit rendre le MÊME thème qu'avant, sans quoi le rattachement
-- posé par le script était faux quelque part.
INSERT INTO _controle_019 (test, ok)
SELECT 'ce thème est bien celui que portait la colonne supprimée',
       (SELECT COUNT(*) FROM exercise_prompt p
          JOIN chapter ch ON ch.id = p.chapter_id
         WHERE ch.theme_id = p.theme_id)
       = (SELECT COUNT(*) FROM exercise_prompt);

INSERT INTO _controle_019 (test, ok)
SELECT 'chaque exercice pointe toujours sur un lancement existant',
       (SELECT COUNT(*) FROM exercise e
         WHERE e.exercise_prompt_id IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM exercise_prompt_neuf p
                            WHERE p.id = e.exercise_prompt_id)) = 0;

-- ---------------------------------------------------------------------
-- L'échange
-- ---------------------------------------------------------------------

DROP TABLE exercise_prompt;
ALTER TABLE exercise_prompt_neuf RENAME TO exercise_prompt;

-- ix_exercise_prompt_theme (theme_id, status) tombe avec sa colonne. Le
-- filtre par thème passe désormais par `chapter`, qui a déjà
-- ix_chapter_theme (theme_id, status).
CREATE INDEX ix_exercise_prompt_chapter ON exercise_prompt (chapter_id, status);
CREATE INDEX ix_exercise_prompt_parent  ON exercise_prompt (parent_id);

DROP TABLE _controle_019;

COMMIT;

PRAGMA integrity_check;
PRAGMA foreign_key_check;
