-- =====================================================================
-- 003 — pays, et catalogue de panneaux
--
-- Deux ajouts liés mais distincts :
--
--   · le PAYS. Jusqu'ici seule la langue distinguait les contenus. Pour
--     du réglementaire, c'est insuffisant : servir la priorité à droite
--     française à quelqu'un qui conduit au Texas n'est pas une nuance,
--     c'est une réponse fausse. Et pays ≠ langue — le Québec lit le
--     français et suit un autre code.
--     `country` est NULLABLE : la mythologie grecque n'a pas de pays.
--     NULL = universel, servi à tout le monde.
--
--   · le CATALOGUE DE PANNEAUX. C'est lui qui garantit qu'une image
--     correspond à sa question. On ne génère pas une question puis on
--     lui cherche une image : on part d'une ligne du catalogue, et
--     l'exercice pointe dessus par clé étrangère. Il n'existe aucune
--     étape où quelqu'un choisit une image, donc rien à se tromper.
--
--   sqlite3 data/sara.db < db/migrations/003_pays_et_panneaux.sql
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Pays
-- ---------------------------------------------------------------------

ALTER TABLE theme    ADD COLUMN country TEXT NULL;   -- ISO 3166-1 : 'FR', 'US'
ALTER TABLE app_user ADD COLUMN country TEXT NULL;

-- Le feed filtre sur (langue, pays, visibilité) : l'index doit porter
-- les trois, sinon on scanne tout le catalogue à chaque exercice servi.
DROP INDEX IF EXISTS ix_theme_lang;
CREATE INDEX ix_theme_feed_lang ON theme (lang, country, visibility);

-- ---------------------------------------------------------------------
-- Catalogue de panneaux
--
-- Ce n'est PAS du contenu généré : c'est de la donnée de référence,
-- recopiée d'une source officielle et vérifiée une fois. C'est ce qui
-- fait tenir la garantie image ↔ question.
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS sign (
  id       INTEGER PRIMARY KEY,
  country  TEXT NOT NULL CHECK (country IN ('FR', 'US')),
  -- Code officiel : 'A1a', 'B14' côté français ; 'R1-9', 'W4-4aP' côté
  -- américain. C'est la clé métier.
  code     TEXT NOT NULL,
  -- Famille : danger, prescription, indication, intersection…
  family   TEXT NULL,

  -- Nom officiel, tel qu'il figure dans la source.
  name     TEXT NOT NULL,
  -- Ce que le panneau signifie. C'est CE champ que la bonne réponse
  -- d'un exercice doit reprendre — le contrôle est automatisable.
  meaning  TEXT NOT NULL,

  image_path TEXT NULL,          -- /media/signs/fr/A1a.svg
  -- Toujours renseigné : un exercice visuel doit rester utilisable au
  -- lecteur d'écran, et le texte alternatif sert aussi de garde-fou à
  -- la relecture.
  image_alt  TEXT NULL,

  -- D'où vient le fichier, et sous quelle licence. Les SVG français
  -- viennent de Wikimedia en CC BY-SA : l'attribution est obligatoire,
  -- donc elle est stockée, pas laissée à la mémoire de quelqu'un.
  source_url     TEXT NULL,
  license        TEXT NULL,
  attribution    TEXT NULL,

  -- 'imported'  : récupéré automatiquement, pas encore relu
  -- 'verified'  : un humain a confirmé que l'image est bien ce code
  -- 'rejected'  : image douteuse ou introuvable, à ne pas utiliser
  -- Seuls les 'verified' peuvent porter un exercice visuel.
  review_state TEXT NOT NULL DEFAULT 'imported'
               CHECK (review_state IN ('imported', 'verified', 'rejected')),

  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (country, code)
);

CREATE INDEX IF NOT EXISTS ix_sign_country ON sign (country, review_state);

-- ---------------------------------------------------------------------
-- Le lien qui porte la garantie
--
-- Une clé étrangère, pas une URL recopiée : l'image affichée EST celle
-- du panneau à partir duquel la question a été écrite. Il n'y a pas de
-- chemin par lequel les deux pourraient diverger.
-- ---------------------------------------------------------------------

ALTER TABLE exercise ADD COLUMN sign_id INTEGER NULL REFERENCES sign (id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_exercise_sign ON exercise (sign_id);
