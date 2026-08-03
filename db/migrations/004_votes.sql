-- =====================================================================
-- 004 — vote communautaire, et quarantaine automatique
--
-- Le cahier des charges disait « pas de je n'aime pas ». On revient
-- dessus délibérément : sans relecture manuelle, c'est la communauté
-- qui détecte les exercices fautifs, et il lui faut un moyen de le dire.
--
-- Le vote n'est pas qu'un signal, c'est une PORTE. Un exercice qui
-- récolte trop de pouces en bas sort du flux tout seul et repasse en
-- 'draft'. Personne ne relit, mais une erreur ne circule pas longtemps.
--
--   sqlite3 data/sara.db < db/migrations/004_votes.sql
-- =====================================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS exercise_vote (
  user_id     INTEGER NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
  exercise_id INTEGER NOT NULL REFERENCES exercise (id) ON DELETE CASCADE,
  -- +1 pouce en haut, -1 pouce en bas. Pas de zéro : ne pas voter,
  -- c'est ne pas avoir de ligne.
  value       INTEGER NOT NULL CHECK (value IN (-1, 1)),
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (user_id, exercise_id)
);

CREATE INDEX IF NOT EXISTS ix_exercise_vote_exercise ON exercise_vote (exercise_id, value);

-- Les j'aime existants deviennent des pouces en haut : personne ne perd
-- son geste.
INSERT OR IGNORE INTO exercise_vote (user_id, exercise_id, value, created_at)
SELECT user_id, exercise_id, 1, created_at FROM exercise_like;

DROP TABLE IF EXISTS exercise_like;

ALTER TABLE exercise ADD COLUMN up_count   INTEGER NOT NULL DEFAULT 0;
ALTER TABLE exercise ADD COLUMN down_count INTEGER NOT NULL DEFAULT 0;

UPDATE exercise SET
  up_count   = (SELECT COUNT(*) FROM exercise_vote v WHERE v.exercise_id = exercise.id AND v.value =  1),
  down_count = (SELECT COUNT(*) FROM exercise_vote v WHERE v.exercise_id = exercise.id AND v.value = -1);

-- ---------------------------------------------------------------------
-- Ce que « trop de pouces en bas » veut dire
--
-- Deux garde-fous, pas un :
--   · un minimum de votes, sinon un seul mécontent suffirait à retirer
--     un bon exercice ;
--   · une proportion, pas un compte absolu, sinon un exercice très vu
--     serait retiré alors qu'il plaît à la majorité.
--
-- Ces valeurs sont un point de départ à ajuster sur des vrais chiffres.
-- ---------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS v_exercise_health AS
SELECT
  e.id AS exercise_id,
  e.theme_id,
  e.state,
  e.up_count,
  e.down_count,
  e.up_count + e.down_count AS votes,
  CASE WHEN e.up_count + e.down_count = 0 THEN NULL
       ELSE ROUND(100.0 * e.down_count / (e.up_count + e.down_count))
  END AS down_pct,
  CASE WHEN e.up_count + e.down_count >= 5
         AND e.down_count > e.up_count
       THEN 1 ELSE 0 END AS should_quarantine
FROM exercise e;
