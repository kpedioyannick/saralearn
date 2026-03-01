<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Platforms\SQLitePlatform;
use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20250227120000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Create classroom, subject, chapter, subchapter tables (SaraLearn school data).';
    }

    public function up(Schema $schema): void
    {
        $isSqlite = $this->connection->getDatabasePlatform() instanceof SQLitePlatform;

        if ($isSqlite) {
            $this->addSql('CREATE TABLE classroom (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                name VARCHAR(64) NOT NULL,
                slug VARCHAR(128) NOT NULL,
                cycle VARCHAR(32) NOT NULL,
                CONSTRAINT uq_classroom_cycle_slug UNIQUE (cycle, slug)
            )');
            $this->addSql('CREATE TABLE subject (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                name VARCHAR(128) NOT NULL,
                slug VARCHAR(255) NOT NULL,
                classroom_id INTEGER NOT NULL,
                CONSTRAINT fk_subject_classroom FOREIGN KEY (classroom_id) REFERENCES classroom (id) ON DELETE CASCADE,
                CONSTRAINT uq_subject_classroom_slug UNIQUE (classroom_id, slug)
            )');
            $this->addSql('CREATE INDEX idx_subject_classroom ON subject (classroom_id)');
            $this->addSql('CREATE TABLE chapter (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                title VARCHAR(255) NOT NULL,
                slug VARCHAR(255) NOT NULL,
                subject_id INTEGER NOT NULL,
                CONSTRAINT fk_chapter_subject FOREIGN KEY (subject_id) REFERENCES subject (id) ON DELETE CASCADE,
                CONSTRAINT uq_chapter_subject_slug UNIQUE (subject_id, slug)
            )');
            $this->addSql('CREATE INDEX idx_chapter_subject ON chapter (subject_id)');
            $this->addSql('CREATE TABLE subchapter (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                title VARCHAR(512) NOT NULL,
                slug VARCHAR(512) NOT NULL,
                href VARCHAR(1024) DEFAULT NULL,
                type VARCHAR(32) DEFAULT NULL,
                chapter_id INTEGER NOT NULL,
                CONSTRAINT fk_subchapter_chapter FOREIGN KEY (chapter_id) REFERENCES chapter (id) ON DELETE CASCADE,
                CONSTRAINT uq_subchapter_chapter_slug UNIQUE (chapter_id, slug)
            )');
            $this->addSql('CREATE INDEX idx_subchapter_chapter ON subchapter (chapter_id)');
        } else {
            $this->addSql('CREATE TABLE classroom (
                id SERIAL PRIMARY KEY,
                name VARCHAR(64) NOT NULL,
                slug VARCHAR(128) NOT NULL,
                cycle VARCHAR(32) NOT NULL,
                CONSTRAINT uq_classroom_cycle_slug UNIQUE (cycle, slug)
            )');
            $this->addSql('CREATE TABLE subject (
                id SERIAL PRIMARY KEY,
                name VARCHAR(128) NOT NULL,
                slug VARCHAR(255) NOT NULL,
                classroom_id INT NOT NULL,
                CONSTRAINT fk_subject_classroom FOREIGN KEY (classroom_id) REFERENCES classroom (id) ON DELETE CASCADE,
                CONSTRAINT uq_subject_classroom_slug UNIQUE (classroom_id, slug)
            )');
            $this->addSql('CREATE INDEX idx_subject_classroom ON subject (classroom_id)');
            $this->addSql('CREATE TABLE chapter (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                slug VARCHAR(255) NOT NULL,
                subject_id INT NOT NULL,
                CONSTRAINT fk_chapter_subject FOREIGN KEY (subject_id) REFERENCES subject (id) ON DELETE CASCADE,
                CONSTRAINT uq_chapter_subject_slug UNIQUE (subject_id, slug)
            )');
            $this->addSql('CREATE INDEX idx_chapter_subject ON chapter (subject_id)');
            $this->addSql('CREATE TABLE subchapter (
                id SERIAL PRIMARY KEY,
                title VARCHAR(512) NOT NULL,
                slug VARCHAR(512) NOT NULL,
                href VARCHAR(1024) DEFAULT NULL,
                type VARCHAR(32) DEFAULT NULL,
                chapter_id INT NOT NULL,
                CONSTRAINT fk_subchapter_chapter FOREIGN KEY (chapter_id) REFERENCES chapter (id) ON DELETE CASCADE,
                CONSTRAINT uq_subchapter_chapter_slug UNIQUE (chapter_id, slug)
            )');
            $this->addSql('CREATE INDEX idx_subchapter_chapter ON subchapter (chapter_id)');
        }
    }

    public function down(Schema $schema): void
    {
        $this->addSql('DROP TABLE IF EXISTS subchapter');
        $this->addSql('DROP TABLE IF EXISTS chapter');
        $this->addSql('DROP TABLE IF EXISTS subject');
        $this->addSql('DROP TABLE IF EXISTS classroom');
    }
}
