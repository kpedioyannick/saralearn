<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

/**
 * Auto-generated Migration: Please modify to your needs!
 */
final class Version20260307123826 extends AbstractMigration
{
    public function getDescription(): string
    {
        return '';
    }

    public function up(Schema $schema): void
    {
        // this up() migration is auto-generated, please modify it to your needs
        $this->addSql('ALTER TABLE course_music ADD COLUMN active VARCHAR(32) DEFAULT NULL');
    }

    public function down(Schema $schema): void
    {
        // this down() migration is auto-generated, please modify it to your needs
        $this->addSql('CREATE TEMPORARY TABLE __temp__course_music AS SELECT id, suno_task_id, suno_clip_id, audio_url, video_url, cover_url, prompt, title, style, relevance, duration, created_at, subchapter_id FROM course_music');
        $this->addSql('DROP TABLE course_music');
        $this->addSql('CREATE TABLE course_music (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, suno_task_id VARCHAR(255) DEFAULT NULL, suno_clip_id VARCHAR(255) DEFAULT NULL, audio_url VARCHAR(2048) DEFAULT NULL, video_url VARCHAR(2048) DEFAULT NULL, cover_url VARCHAR(2048) DEFAULT NULL, prompt CLOB DEFAULT NULL, title VARCHAR(255) DEFAULT NULL, style VARCHAR(2048) DEFAULT NULL, relevance VARCHAR(64) DEFAULT NULL, duration DOUBLE PRECISION DEFAULT NULL, created_at DATETIME NOT NULL, subchapter_id INTEGER NOT NULL, CONSTRAINT FK_24F925A280EA0CB FOREIGN KEY (subchapter_id) REFERENCES subchapter (id) ON DELETE CASCADE NOT DEFERRABLE INITIALLY IMMEDIATE)');
        $this->addSql('INSERT INTO course_music (id, suno_task_id, suno_clip_id, audio_url, video_url, cover_url, prompt, title, style, relevance, duration, created_at, subchapter_id) SELECT id, suno_task_id, suno_clip_id, audio_url, video_url, cover_url, prompt, title, style, relevance, duration, created_at, subchapter_id FROM __temp__course_music');
        $this->addSql('DROP TABLE __temp__course_music');
        $this->addSql('CREATE INDEX IDX_24F925A280EA0CB ON course_music (subchapter_id)');
    }
}
