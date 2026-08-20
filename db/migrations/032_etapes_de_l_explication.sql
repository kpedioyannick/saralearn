-- L'EXPLICATION DEVIENT UNE SUITE D'ÉTAPES, chacune avec son image.
--
-- Jusqu'ici `exp_text` était un bloc, et le front le redécoupait à
-- l'affichage, phrase par phrase, DANS CHAQUE LANGUE SÉPARÉMENT.
-- Conséquence mesurée : 14 cartes sur 261 n'ont pas le même nombre
-- d'étapes en français et en anglais — la 210 en a 5 d'un côté, 3 de
-- l'autre. Attacher une image au rang d'une étape sur cette base
-- décalerait les images pour un lecteur sur vingt.
--
-- Le découpage est donc figé ici, une fois, du côté de la source. Le
-- rang est la clé : c'est lui que la traduction et l'image partagent.
--
-- `exp_text` N'EST PAS SUPPRIMÉ : la voix le lit d'un trait, le front
-- actuel l'affiche, et rien ne doit casser tant que l'écran n'a pas
-- changé. Les étapes le doublent, elles ne le remplacent pas encore.

CREATE TABLE IF NOT EXISTS exercise_step (
  exercise_id       INTEGER NOT NULL REFERENCES exercise(id) ON DELETE CASCADE,
  rang              INTEGER NOT NULL,
  texte             TEXT    NOT NULL,

  -- LE TITRE DE L'IMAGE À ALLER CHERCHER, écrit par le modèle au moment
  -- où il écrit l'étape. Il nomme ce qu'il faut montrer, pas ce que la
  -- question cache : sur l'écran d'explication la réponse est déjà
  -- donnée, `photos.revele` ne s'applique donc pas ici.
  image_title       TEXT,

  image_url         TEXT,
  image_alt         TEXT,
  image_credit      TEXT,
  image_credit_url  TEXT,
  image_source      TEXT,

  created_at        TEXT NOT NULL DEFAULT (datetime('now')),

  PRIMARY KEY (exercise_id, rang)
);

CREATE INDEX IF NOT EXISTS idx_step_a_illustrer
  ON exercise_step(exercise_id)
  WHERE image_url IS NULL AND image_title IS NOT NULL;

-- Le texte de l'étape dans les autres langues. L'image, elle, n'est PAS
-- traduite : elle est la même pour tous, ce qui suppose qu'aucun mot ne
-- soit écrit dessus.
CREATE TABLE IF NOT EXISTS exercise_step_translation (
  exercise_id  INTEGER NOT NULL REFERENCES exercise(id) ON DELETE CASCADE,
  rang         INTEGER NOT NULL,
  lang         TEXT    NOT NULL,
  texte        TEXT    NOT NULL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),

  PRIMARY KEY (exercise_id, rang, lang)
);
