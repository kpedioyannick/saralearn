<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

/**
 * Auto-generated Migration: Please modify to your needs!
 */
final class Version20260301160724 extends AbstractMigration
{
    public function getDescription(): string
    {
        return '';
    }

    public function up(Schema $schema): void
    {
        // this up() migration is auto-generated, please modify it to your needs
        $this->addSql('CREATE TABLE app_user (id INT AUTO_INCREMENT NOT NULL, email VARCHAR(180) NOT NULL, display_name VARCHAR(255) DEFAULT NULL, created_at DATETIME NOT NULL, classroom_id INT DEFAULT NULL, UNIQUE INDEX UNIQ_88BDF3E9E7927C74 (email), INDEX IDX_88BDF3E96278D5A8 (classroom_id), PRIMARY KEY (id)) DEFAULT CHARACTER SET utf8mb4');
        $this->addSql('CREATE TABLE chapter (id INT AUTO_INCREMENT NOT NULL, title VARCHAR(1024) NOT NULL, slug VARCHAR(1024) NOT NULL, course JSON DEFAULT NULL, mindmap JSON DEFAULT NULL, subject_id INT NOT NULL, INDEX IDX_F981B52E23EDC87 (subject_id), PRIMARY KEY (id)) DEFAULT CHARACTER SET utf8mb4');
        $this->addSql('CREATE TABLE classroom (id INT AUTO_INCREMENT NOT NULL, name VARCHAR(64) NOT NULL, slug VARCHAR(128) NOT NULL, cycle VARCHAR(32) NOT NULL, UNIQUE INDEX uq_classroom_cycle_slug (cycle, slug), PRIMARY KEY (id)) DEFAULT CHARACTER SET utf8mb4');
        $this->addSql('CREATE TABLE course_music (id INT AUTO_INCREMENT NOT NULL, suno_task_id VARCHAR(255) DEFAULT NULL, audio_url VARCHAR(2048) DEFAULT NULL, prompt LONGTEXT DEFAULT NULL, title VARCHAR(255) DEFAULT NULL, duration DOUBLE PRECISION DEFAULT NULL, created_at DATETIME NOT NULL, subchapter_id INT NOT NULL, INDEX IDX_24F925A280EA0CB (subchapter_id), PRIMARY KEY (id)) DEFAULT CHARACTER SET utf8mb4');
        $this->addSql('CREATE TABLE learning_path (id INT AUTO_INCREMENT NOT NULL, category VARCHAR(64) NOT NULL, title VARCHAR(512) NOT NULL, types JSON DEFAULT NULL, output_path VARCHAR(1024) NOT NULL, created_at DATETIME NOT NULL, chapter_id INT NOT NULL, subchapter_id INT DEFAULT NULL, INDEX IDX_4D04C797579F4768 (chapter_id), INDEX IDX_4D04C79780EA0CB (subchapter_id), PRIMARY KEY (id)) DEFAULT CHARACTER SET utf8mb4');
        $this->addSql('CREATE TABLE learning_path_learner (learning_path_id INT NOT NULL, user_id INT NOT NULL, INDEX IDX_6BAA1B4A1DCBEE98 (learning_path_id), INDEX IDX_6BAA1B4AA76ED395 (user_id), PRIMARY KEY (learning_path_id, user_id)) DEFAULT CHARACTER SET utf8mb4');
        $this->addSql('CREATE TABLE module (id INT AUTO_INCREMENT NOT NULL, title VARCHAR(512) NOT NULL, bloom_level VARCHAR(32) NOT NULL, difficulty VARCHAR(32) NOT NULL, h5p_type VARCHAR(64) NOT NULL, content LONGTEXT NOT NULL, created_at DATETIME NOT NULL, subchapter_id INT NOT NULL, chapter_id INT NOT NULL, path_id INT DEFAULT NULL, INDEX IDX_C24262880EA0CB (subchapter_id), INDEX IDX_C242628579F4768 (chapter_id), INDEX IDX_C242628D96C566B (path_id), PRIMARY KEY (id)) DEFAULT CHARACTER SET utf8mb4');
        $this->addSql('CREATE TABLE subchapter (id INT AUTO_INCREMENT NOT NULL, title VARCHAR(1024) NOT NULL, slug VARCHAR(1024) NOT NULL, href VARCHAR(1024) DEFAULT NULL, type VARCHAR(32) DEFAULT NULL, course JSON DEFAULT NULL, mindmap JSON DEFAULT NULL, chapter_id INT NOT NULL, INDEX IDX_B2E31DE1579F4768 (chapter_id), PRIMARY KEY (id)) DEFAULT CHARACTER SET utf8mb4');
        $this->addSql('CREATE TABLE subject (id INT AUTO_INCREMENT NOT NULL, name VARCHAR(1024) NOT NULL, slug VARCHAR(1024) NOT NULL, classroom_id INT NOT NULL, INDEX IDX_FBCE3E7A6278D5A8 (classroom_id), PRIMARY KEY (id)) DEFAULT CHARACTER SET utf8mb4');
        $this->addSql('CREATE TABLE messenger_messages (id BIGINT AUTO_INCREMENT NOT NULL, body LONGTEXT NOT NULL, headers LONGTEXT NOT NULL, queue_name VARCHAR(190) NOT NULL, created_at DATETIME NOT NULL, available_at DATETIME NOT NULL, delivered_at DATETIME DEFAULT NULL, INDEX IDX_75EA56E0FB7336F0E3BD61CE16BA31DBBF396750 (queue_name, available_at, delivered_at, id), PRIMARY KEY (id)) DEFAULT CHARACTER SET utf8mb4');
        $this->addSql('ALTER TABLE app_user ADD CONSTRAINT FK_88BDF3E96278D5A8 FOREIGN KEY (classroom_id) REFERENCES classroom (id) ON DELETE SET NULL');
        $this->addSql('ALTER TABLE chapter ADD CONSTRAINT FK_F981B52E23EDC87 FOREIGN KEY (subject_id) REFERENCES subject (id)');
        $this->addSql('ALTER TABLE course_music ADD CONSTRAINT FK_24F925A280EA0CB FOREIGN KEY (subchapter_id) REFERENCES subchapter (id) ON DELETE CASCADE');
        $this->addSql('ALTER TABLE learning_path ADD CONSTRAINT FK_4D04C797579F4768 FOREIGN KEY (chapter_id) REFERENCES chapter (id)');
        $this->addSql('ALTER TABLE learning_path ADD CONSTRAINT FK_4D04C79780EA0CB FOREIGN KEY (subchapter_id) REFERENCES subchapter (id) ON DELETE CASCADE');
        $this->addSql('ALTER TABLE learning_path_learner ADD CONSTRAINT FK_6BAA1B4A1DCBEE98 FOREIGN KEY (learning_path_id) REFERENCES learning_path (id) ON DELETE CASCADE');
        $this->addSql('ALTER TABLE learning_path_learner ADD CONSTRAINT FK_6BAA1B4AA76ED395 FOREIGN KEY (user_id) REFERENCES app_user (id) ON DELETE CASCADE');
        $this->addSql('ALTER TABLE module ADD CONSTRAINT FK_C24262880EA0CB FOREIGN KEY (subchapter_id) REFERENCES subchapter (id)');
        $this->addSql('ALTER TABLE module ADD CONSTRAINT FK_C242628579F4768 FOREIGN KEY (chapter_id) REFERENCES chapter (id)');
        $this->addSql('ALTER TABLE module ADD CONSTRAINT FK_C242628D96C566B FOREIGN KEY (path_id) REFERENCES learning_path (id) ON DELETE SET NULL');
        $this->addSql('ALTER TABLE subchapter ADD CONSTRAINT FK_B2E31DE1579F4768 FOREIGN KEY (chapter_id) REFERENCES chapter (id)');
        $this->addSql('ALTER TABLE subject ADD CONSTRAINT FK_FBCE3E7A6278D5A8 FOREIGN KEY (classroom_id) REFERENCES classroom (id)');
    }

    public function down(Schema $schema): void
    {
        // this down() migration is auto-generated, please modify it to your needs
        $this->addSql('ALTER TABLE app_user DROP FOREIGN KEY FK_88BDF3E96278D5A8');
        $this->addSql('ALTER TABLE chapter DROP FOREIGN KEY FK_F981B52E23EDC87');
        $this->addSql('ALTER TABLE course_music DROP FOREIGN KEY FK_24F925A280EA0CB');
        $this->addSql('ALTER TABLE learning_path DROP FOREIGN KEY FK_4D04C797579F4768');
        $this->addSql('ALTER TABLE learning_path DROP FOREIGN KEY FK_4D04C79780EA0CB');
        $this->addSql('ALTER TABLE learning_path_learner DROP FOREIGN KEY FK_6BAA1B4A1DCBEE98');
        $this->addSql('ALTER TABLE learning_path_learner DROP FOREIGN KEY FK_6BAA1B4AA76ED395');
        $this->addSql('ALTER TABLE module DROP FOREIGN KEY FK_C24262880EA0CB');
        $this->addSql('ALTER TABLE module DROP FOREIGN KEY FK_C242628579F4768');
        $this->addSql('ALTER TABLE module DROP FOREIGN KEY FK_C242628D96C566B');
        $this->addSql('ALTER TABLE subchapter DROP FOREIGN KEY FK_B2E31DE1579F4768');
        $this->addSql('ALTER TABLE subject DROP FOREIGN KEY FK_FBCE3E7A6278D5A8');
        $this->addSql('DROP TABLE app_user');
        $this->addSql('DROP TABLE chapter');
        $this->addSql('DROP TABLE classroom');
        $this->addSql('DROP TABLE course_music');
        $this->addSql('DROP TABLE learning_path');
        $this->addSql('DROP TABLE learning_path_learner');
        $this->addSql('DROP TABLE module');
        $this->addSql('DROP TABLE subchapter');
        $this->addSql('DROP TABLE subject');
        $this->addSql('DROP TABLE messenger_messages');
    }
}
