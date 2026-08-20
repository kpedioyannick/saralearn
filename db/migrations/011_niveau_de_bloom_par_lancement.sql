-- =====================================================================
-- 011 — le niveau de Bloom d'un lancement issu d'un chapitre
--
-- Le découpage en chapitres avait remplacé le classement de Bloom. Le
-- commentaire de `api/routers/generate.py` le disait franchement :
--
--   « Un lancement issu d'un chapitre n'a pas de niveau de Bloom : le
--     découpage en chapitres remplace ce classement, et la colonne
--     reste NOT NULL. `understand` est le niveau moyen des gabarits. »
--
-- À l'usage, non. Un chapitre dit CE QU'ON APPREND ; le niveau dit CE
-- QU'ON EXIGE de l'élève dessus — se rappeler d'un intitulé, ou trancher
-- un cas qu'il n'a jamais vu. Les deux sont indépendants, et les
-- confondre a produit ce qu'on pouvait prévoir : les 39 premiers
-- exercices anglais sont sortis à 39 sur 39 en `understand`, difficulté
-- 2, sans une seule marche de progression.
--
-- C'est aussi ce qui rend le prompt d'un chapitre réutilisable pour de
-- bon. Il reste générique — il ne porte aucun niveau — et c'est le
-- lancement qui en choisit un. Quatre lancements sur le même prompt
-- donnent quatre lots DIFFÉRENTS PAR CONSTRUCTION, là où quatre
-- lancements identiques ne donnaient que des variantes.
--
-- NULLABLE, et il doit le rester. Deux lancements sur trois n'en auront
-- jamais : ceux qui citent un gabarit de la table `prompt` tiennent
-- déjà leur niveau de lui (`prompt.type_bloom`), et les 156 lancements
-- déjà en base viennent d'un temps où la question ne se posait pas. Les
-- laisser à NULL dit la vérité ; les remplir d'un `understand` supposé
-- inventerait une donnée que personne n'a décidée.
--
-- Les valeurs reprennent le CHECK d'`exercise.type_bloom` : un lancement
-- ne peut pas demander un niveau que l'exercice produit ne saurait
-- porter. `evaluate` et `create`, les deux étages hauts de Bloom, n'y
-- sont pas — les ajouter imposerait de reconstruire `exercise` et ses
-- 994 lignes, et `analyze` couvre déjà « repérer ce qui cloche ».
--
--   python3 scripts/migrate.py db/migrations/011_niveau_de_bloom_par_lancement.sql
-- =====================================================================

BEGIN;

ALTER TABLE exercise_prompt ADD COLUMN type_bloom TEXT
  CHECK (type_bloom IS NULL
         OR type_bloom IN ('remember', 'understand', 'apply', 'analyze'));

-- Le script d'import demande « ce chapitre a-t-il déjà été servi À CE
-- NIVEAU ? » avant chaque lancement. Sans index, c'est un balayage par
-- couple (chapitre × niveau), soit une soixantaine de balayages pour un
-- import complet.
CREATE INDEX IF NOT EXISTS ix_exercise_prompt_chapter_bloom
  ON exercise_prompt (chapter_id, type_bloom, status);

COMMIT;

PRAGMA integrity_check;
PRAGMA foreign_key_check;
