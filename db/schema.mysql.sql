-- =====================================================================
-- Sara — app d'exercices · schéma
--
-- ⚠ CE FICHIER NE REPRODUIT PLUS LA BASE. Il date du démarrage et n'a
-- pas suivi les 19 migrations. Il lui manque `chapter` et `sign`, il
-- déclare `exercise_like` là où la base a `exercise_vote`, et il garde
-- des bornes de longueur retirées par la 015. La vérité est dans
-- `data/sara.db (SQLite)` et dans `db/migrations/`. Ne pas s'en servir pour
-- recréer la base.
--
-- On part de zéro : pas de H5P, pas de reprise de sara_learn.
-- La source d'un thème est du Markdown, découpé en chapitres ; chaque
-- chapitre commande un lancement, et un lancement écrit ses exercices.
--
--   category ─┬─ sub_category ─┐
--             └────────────────┴─> theme ─< theme_tag >─ tag
--                                    │
--                                    └─< exercise_prompt >─┐ (parent_id)
--                                             │  ^─────────┘
--                                             └─< exercise
--
-- MySQL 8 · InnoDB · utf8mb4
-- =====================================================================

CREATE DATABASE IF NOT EXISTS sara_exos
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE sara_exos;

-- ---------------------------------------------------------------------
-- Taxonomie
-- ---------------------------------------------------------------------

CREATE TABLE category (
  id         INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  slug       VARCHAR(96)     NOT NULL,
  label      VARCHAR(160)    NOT NULL,
  -- La maquette donne une couleur à chaque catégorie ; elle est héritée
  -- par les thèmes qui n'en définissent pas.
  color      CHAR(7)         NOT NULL DEFAULT '#0A5C2C',
  position   SMALLINT        NOT NULL DEFAULT 0,
  created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_category_slug (slug)
) ENGINE = InnoDB;

CREATE TABLE sub_category (
  id          INT UNSIGNED   NOT NULL AUTO_INCREMENT,
  category_id INT UNSIGNED   NOT NULL,
  slug        VARCHAR(96)    NOT NULL,
  label       VARCHAR(160)   NOT NULL,
  color       CHAR(7)        NULL,
  position    SMALLINT       NOT NULL DEFAULT 0,
  created_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_sub_category_slug (category_id, slug),
  KEY ix_sub_category_category (category_id),
  CONSTRAINT fk_sub_category_category
    FOREIGN KEY (category_id) REFERENCES category (id) ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE TABLE tag (
  id    INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  slug  VARCHAR(96)   NOT NULL,
  label VARCHAR(160)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_tag_slug (slug)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- Thème — l'unité à laquelle on s'abonne, et la source Markdown
-- ---------------------------------------------------------------------

CREATE TABLE theme (
  id              INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  -- category_id est dénormalisé : sub_category le porte déjà, mais un
  -- thème peut exister sans sous-catégorie et le flux de création
  -- demande les deux séparément.
  category_id     INT UNSIGNED  NOT NULL,
  sub_category_id INT UNSIGNED  NULL,
  owner_id        INT UNSIGNED  NULL,

  slug            VARCHAR(160)  NOT NULL,
  title           VARCHAR(255)  NOT NULL,
  description     TEXT          NULL,
  color           CHAR(7)       NULL,

  -- La source déposée par l'auteur. C'est elle qu'on donne au modèle.
  source_markdown MEDIUMTEXT    NULL,

  -- private : visible du seul auteur (défaut)
  -- pending : relecture demandée
  -- public  : visible de tous
  visibility      ENUM('private','pending','public') NOT NULL DEFAULT 'private',

  exercise_count  INT UNSIGNED  NOT NULL DEFAULT 0,
  subscriber_count INT UNSIGNED NOT NULL DEFAULT 0,

  created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
  published_at    DATETIME      NULL,

  PRIMARY KEY (id),
  UNIQUE KEY uq_theme_slug (slug),
  KEY ix_theme_category (category_id),
  KEY ix_theme_sub_category (sub_category_id),
  KEY ix_theme_owner (owner_id),
  -- Le feed ne tire que dans le public ; cet index porte la requête.
  KEY ix_theme_feed (visibility, sub_category_id),
  CONSTRAINT fk_theme_category
    FOREIGN KEY (category_id) REFERENCES category (id),
  CONSTRAINT fk_theme_sub_category
    FOREIGN KEY (sub_category_id) REFERENCES sub_category (id) ON DELETE SET NULL
) ENGINE = InnoDB;

CREATE TABLE theme_tag (
  theme_id INT UNSIGNED NOT NULL,
  tag_id   INT UNSIGNED NOT NULL,
  PRIMARY KEY (theme_id, tag_id),
  KEY ix_theme_tag_tag (tag_id),
  CONSTRAINT fk_theme_tag_theme
    FOREIGN KEY (theme_id) REFERENCES theme (id) ON DELETE CASCADE,
  CONSTRAINT fk_theme_tag_tag
    FOREIGN KEY (tag_id) REFERENCES tag (id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- Lancements — un texte envoyé au modèle, et ce qu'il en est sorti
-- ---------------------------------------------------------------------

-- Une exécution : ce thème, ce texte réellement envoyé, ce qui en est né.
-- Permet de remonter d'un exercice douteux au prompt exact qui l'a écrit.
-- `parent_id` pointe vers un autre lancement : une recharge de feed
-- rejoue la consigne d'un lancement antérieur et se déclare son enfant.
CREATE TABLE exercise_prompt (
  id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  chapter_id      INT UNSIGNED NOT NULL,
  parent_id       INT UNSIGNED NULL,

  rendered_prompt MEDIUMTEXT   NOT NULL,
  model           VARCHAR(96)  NULL,
  requested_count SMALLINT UNSIGNED NOT NULL DEFAULT 10,
  produced_count  SMALLINT UNSIGNED NOT NULL DEFAULT 0,

  status          ENUM('pending','running','done','failed') NOT NULL DEFAULT 'pending',
  error           TEXT         NULL,

  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at     DATETIME     NULL,

  PRIMARY KEY (id),
  KEY ix_exercise_prompt_chapter (chapter_id, status),
  KEY ix_exercise_prompt_parent (parent_id),
  -- Une ligne sa propre mère : interdit. MySQL vérifie les CHECK
  -- depuis 8.0.16 ; en deçà, la clause est acceptée puis ignorée.
  CONSTRAINT ck_exercise_prompt_parent CHECK (parent_id IS NULL OR parent_id <> id),
  CONSTRAINT fk_exercise_prompt_chapter
    FOREIGN KEY (chapter_id) REFERENCES chapter (id) ON DELETE CASCADE,
  CONSTRAINT fk_exercise_prompt_parent
    FOREIGN KEY (parent_id) REFERENCES exercise_prompt (id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- Exercice — exactement les champs que l'écran consomme
-- ---------------------------------------------------------------------

CREATE TABLE exercise (
  id                 INT UNSIGNED NOT NULL AUTO_INCREMENT,
  theme_id           INT UNSIGNED NOT NULL,
  exercise_prompt_id INT UNSIGNED NULL,

  type_question ENUM('qcm','true_false','complete','find_error','reorder') NOT NULL,

  -- Écran exercice. Limites de longueur imposées ici plutôt que dans
  -- l'UI : « un écran, pas de scroll » se tient à l'écriture.
  prompt        VARCHAR(240) NOT NULL,
  -- Production fautive à localiser — seulement sur find_error.
  body          VARCHAR(400) NULL,
  -- [{ "label": "…", "feedback": "…" }] — 2 à 4 entrées
  options       JSON         NOT NULL,
  correct_index TINYINT UNSIGNED NOT NULL,

  -- Écrans félicitation / erreur / explication
  ok_title      VARCHAR(80)  NULL,
  ok_line       VARCHAR(200) NULL,
  ko_title      VARCHAR(80)  NULL,
  ko_line       VARCHAR(200) NULL,
  exp_title     VARCHAR(160) NULL,
  exp_text      VARCHAR(600) NOT NULL,

  -- draft     : sorti du modèle, pas encore relu
  -- validated : relu, servi dans le feed
  -- rejected  : écarté, conservé pour améliorer le prompt
  state         ENUM('draft','validated','rejected') NOT NULL DEFAULT 'draft',

  like_count    INT UNSIGNED NOT NULL DEFAULT 0,
  attempt_count INT UNSIGNED NOT NULL DEFAULT 0,

  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  -- L'index qui porte le feed : thème abonné + validé.
  KEY ix_exercise_feed (theme_id, state),
  KEY ix_exercise_prompt_run (exercise_prompt_id),
  CONSTRAINT fk_exercise_theme
    FOREIGN KEY (theme_id) REFERENCES theme (id) ON DELETE CASCADE,
  CONSTRAINT fk_exercise_prompt_run
    FOREIGN KEY (exercise_prompt_id) REFERENCES exercise_prompt (id) ON DELETE SET NULL,
  CONSTRAINT ck_exercise_correct_index CHECK (correct_index < 4)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- Utilisateur et activité
-- ---------------------------------------------------------------------

CREATE TABLE app_user (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  -- L'app ouvre sur un exercice, sans compte : device_id identifie la
  -- session anonyme, l'email n'arrive que si le compte est créé.
  device_id     CHAR(36)     NOT NULL,
  email         VARCHAR(255) NULL,
  password_hash VARCHAR(255) NULL,
  display_name  VARCHAR(120) NULL,
  is_admin      TINYINT(1)   NOT NULL DEFAULT 0,
  muted         TINYINT(1)   NOT NULL DEFAULT 0,
  dark          TINYINT(1)   NULL,
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_seen_at  DATETIME     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_app_user_device (device_id),
  UNIQUE KEY uq_app_user_email (email)
) ENGINE = InnoDB;

-- Abonnements : ce que l'écran Paramètres coche et décoche.
CREATE TABLE user_theme (
  user_id    INT UNSIGNED NOT NULL,
  theme_id   INT UNSIGNED NOT NULL,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, theme_id),
  KEY ix_user_theme_theme (theme_id),
  CONSTRAINT fk_user_theme_user
    FOREIGN KEY (user_id) REFERENCES app_user (id) ON DELETE CASCADE,
  CONSTRAINT fk_user_theme_theme
    FOREIGN KEY (theme_id) REFERENCES theme (id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- Compteurs et progression se dérivent d'ici. Pas de table de
-- compteurs : elle finit toujours par se désynchroniser.
CREATE TABLE attempt (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id     INT UNSIGNED NOT NULL,
  exercise_id INT UNSIGNED NOT NULL,
  theme_id    INT UNSIGNED NOT NULL,
  -- NULL = exercice passé au swipe sans répondre.
  chosen_index TINYINT UNSIGNED NULL,
  is_correct  TINYINT(1)   NULL,
  answer_ms   INT UNSIGNED NULL,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  -- Anti-répétition : les N derniers vus par cet utilisateur.
  KEY ix_attempt_recent (user_id, created_at),
  -- Progression par thème.
  KEY ix_attempt_progress (user_id, theme_id, is_correct),
  -- Classement hebdomadaire d'un thème.
  KEY ix_attempt_rank (theme_id, created_at, user_id),
  KEY ix_attempt_exercise (exercise_id),
  CONSTRAINT fk_attempt_user
    FOREIGN KEY (user_id) REFERENCES app_user (id) ON DELETE CASCADE,
  CONSTRAINT fk_attempt_exercise
    FOREIGN KEY (exercise_id) REFERENCES exercise (id) ON DELETE CASCADE,
  CONSTRAINT fk_attempt_theme
    FOREIGN KEY (theme_id) REFERENCES theme (id) ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE TABLE exercise_like (
  user_id     INT UNSIGNED NOT NULL,
  exercise_id INT UNSIGNED NOT NULL,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, exercise_id),
  KEY ix_exercise_like_exercise (exercise_id),
  CONSTRAINT fk_exercise_like_user
    FOREIGN KEY (user_id) REFERENCES app_user (id) ON DELETE CASCADE,
  CONSTRAINT fk_exercise_like_exercise
    FOREIGN KEY (exercise_id) REFERENCES exercise (id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- Le cahier des charges dit « champ libre, envoyé à l'admin ».
CREATE TABLE exercise_comment (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id     INT UNSIGNED NOT NULL,
  exercise_id INT UNSIGNED NOT NULL,
  body        VARCHAR(1000) NOT NULL,
  is_read     TINYINT(1)    NOT NULL DEFAULT 0,
  created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_exercise_comment_exercise (exercise_id, created_at),
  KEY ix_exercise_comment_unread (is_read, created_at),
  CONSTRAINT fk_exercise_comment_user
    FOREIGN KEY (user_id) REFERENCES app_user (id) ON DELETE CASCADE,
  CONSTRAINT fk_exercise_comment_exercise
    FOREIGN KEY (exercise_id) REFERENCES exercise (id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- Vue de progression — les pourcentages ne vivent que là
-- ---------------------------------------------------------------------

-- Barème du classement, en un seul endroit : une bonne réponse vaut 10,
-- une tentative vaut 2. Un exercice passé au swipe ne rapporte rien.
-- Le classement d'un thème repart chaque lundi.
CREATE OR REPLACE VIEW v_theme_week_rank AS
SELECT
  a.theme_id,
  a.user_id,
  DATE(a.created_at - INTERVAL WEEKDAY(a.created_at) DAY) AS week_start,
  SUM(CASE WHEN a.is_correct = 1 THEN 10
           WHEN a.is_correct = 0 THEN 2
           ELSE 0 END)                                    AS points,
  SUM(a.is_correct = 1)                                   AS passed,
  SUM(a.chosen_index IS NOT NULL)                         AS answered
FROM attempt a
GROUP BY a.theme_id, a.user_id,
         DATE(a.created_at - INTERVAL WEEKDAY(a.created_at) DAY);

-- Classement global, toutes périodes — l'onglet « Les autres ».
CREATE OR REPLACE VIEW v_global_rank AS
SELECT
  a.user_id,
  SUM(CASE WHEN a.is_correct = 1 THEN 10
           WHEN a.is_correct = 0 THEN 2
           ELSE 0 END) AS points,
  SUM(a.is_correct = 1) AS passed,
  COUNT(*)              AS attempts
FROM attempt a
GROUP BY a.user_id;

CREATE OR REPLACE VIEW v_user_theme_progress AS
SELECT
  a.user_id,
  a.theme_id,
  COUNT(DISTINCT CASE WHEN a.is_correct = 1 THEN a.exercise_id END) AS passed,
  (SELECT COUNT(*) FROM exercise e
     WHERE e.theme_id = a.theme_id AND e.state = 'validated')       AS total,
  ROUND(
    100 * COUNT(DISTINCT CASE WHEN a.is_correct = 1 THEN a.exercise_id END)
    / NULLIF((SELECT COUNT(*) FROM exercise e
                WHERE e.theme_id = a.theme_id AND e.state = 'validated'), 0)
  )                                                                  AS pct
FROM attempt a
GROUP BY a.user_id, a.theme_id;
