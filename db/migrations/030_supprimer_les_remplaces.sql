-- Suppression des 198 exercices remplacés par la réécriture du 19/08/2026.
--
-- Sur ordre explicite du propriétaire, redonné après avoir vu ce que la
-- cascade emporte. C'est le seul geste irréversible de cette journée, et
-- il faut qu'il reste écrit ici pourquoi il a été fait.
--
-- CE QUI PART AVEC EUX, par `ON DELETE CASCADE` :
--
--   · 197 lignes d'`exercise_translation` — sans intérêt, elles ne
--     servaient que ces exercices ;
--   · **17 lignes d'`attempt` sur 50** — et celles-là comptent. Ce sont
--     de vraies réponses, données par le propriétaire le 19/08. La
--     progression et la série calculées dessus disparaissent avec elles.
--     `attempt.exercise_id` est NOT NULL : on ne peut pas garder la
--     tentative sans l'exercice qu'elle désigne.
--
-- CE QUI NE BOUGE PAS : `chapter.exercise_count` ne compte que le
-- `validated`, il était déjà juste.
--
-- D'où venaient ces 198 : 185 écrits avec la consigne « les définitions
-- à connaître » d'avant le 19/08, remplacés par la consigne d'intuition ;
-- 13 retirés quand « Bird flight » et « 22° halo » ont été réécrits une
-- seconde fois, leur première version ratant une question sur deux.

-- LES ENFANTS D'ABORD, ET EXPLICITEMENT. Les trois tables portent bien
-- un `ON DELETE CASCADE`, mais SQLite désactive les clés étrangères par
-- défaut et `scripts/migrate.py` ne les rallume pas : le premier essai a
-- supprimé les exercices en laissant 214 lignes pendantes, et le
-- contrôle d'orphelins du script a restauré la base. C'est exactement ce
-- pour quoi ce contrôle existe.
--
-- Écrire les quatre suppressions à la main plutôt que d'ajouter un
-- PRAGMA : la cascade est un effet de bord invisible à la lecture, la
-- liste ci-dessous dit ce qui disparaît.

DELETE FROM exercise_comment     WHERE exercise_id IN (SELECT id FROM exercise WHERE state = 'draft');
DELETE FROM exercise_vote        WHERE exercise_id IN (SELECT id FROM exercise WHERE state = 'draft');
DELETE FROM exercise_translation WHERE exercise_id IN (SELECT id FROM exercise WHERE state = 'draft');
DELETE FROM attempt              WHERE exercise_id IN (SELECT id FROM exercise WHERE state = 'draft');
DELETE FROM exercise             WHERE state = 'draft';
