<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Platforms\SQLitePlatform;
use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20250227130000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Create module and learning_path tables (H5P modules and paths).';
    }

    public function up(Schema $schema): void
    {
        $isSqlite = $this->connection->getDatabasePlatform() instanceof SQLitePlatform;

        if ($isSqlite) {
            $this->addSql('CREATE TABLE learning_path (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                category VARCHAR(64) NOT NULL,
                chapter_id INTEGER NOT NULL,
                subchapter_id INTEGER DEFAULT NULL,
                title VARCHAR(512) NOT NULL,
                type VARCHAR(64) DEFAULT NULL,
                output_path VARCHAR(1024) NOT NULL,
                created_at DATETIME NOT NULL,
                CONSTRAINT fk_path_chapter FOREIGN KEY (chapter_id) REFERENCES chapter (id) ON DELETE CASCADE,
                CONSTRAINT fk_path_subchapter FOREIGN KEY (subchapter_id) REFERENCES subchapter (id) ON DELETE SET NULL
            )');
            $this->addSql('CREATE INDEX idx_path_chapter ON learning_path (chapter_id)');
            $this->addSql('CREATE INDEX idx_path_subchapter ON learning_path (subchapter_id)');

            $this->addSql('CREATE TABLE module (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                subchapter_id INTEGER NOT NULL,
                title VARCHAR(512) NOT NULL,
                chapter_id INTEGER NOT NULL,
                bloom_level VARCHAR(32) NOT NULL,
                difficulty VARCHAR(32) NOT NULL,
                h5p_type VARCHAR(64) NOT NULL,
                content TEXT NOT NULL,
                path_id INTEGER DEFAULT NULL,
                created_at DATETIME NOT NULL,
                CONSTRAINT fk_module_subchapter FOREIGN KEY (subchapter_id) REFERENCES subchapter (id) ON DELETE CASCADE,
                CONSTRAINT fk_module_chapter FOREIGN KEY (chapter_id) REFERENCES chapter (id) ON DELETE CASCADE,
                CONSTRAINT fk_module_path FOREIGN KEY (path_id) REFERENCES learning_path (id) ON DELETE SET NULL
            )');
            $this->addSql('CREATE INDEX idx_module_subchapter ON module (subchapter_id)');
            $this->addSql('CREATE INDEX idx_module_chapter ON module (chapter_id)');
            $this->addSql('CREATE INDEX idx_module_path ON module (path_id)');
        } else {
            $this->addSql('CREATE TABLE learning_path (
                id SERIAL PRIMARY KEY,
                category VARCHAR(64) NOT NULL,
                chapter_id INT NOT NULL,
                subchapter_id INT DEFAULT NULL,
                title VARCHAR(512) NOT NULL,
                type VARCHAR(64) DEFAULT NULL,
                output_path VARCHAR(1024) NOT NULL,
                created_at TIMESTAMP(0) WITHOUT TIME ZONE NOT NULL,
                CONSTRAINT fk_path_chapter FOREIGN KEY (chapter_id) REFERENCES chapter (id) ON DELETE CASCADE,
                CONSTRAINT fk_path_subchapter FOREIGN KEY (subchapter_id) REFERENCES subchapter (id) ON DELETE SET NULL
            )');
            $this->addSql('CREATE INDEX idx_path_chapter ON learning_path (chapter_id)');
            $this->addSql('CREATE INDEX idx_path_subchapter ON learning_path (subchapter_id)');

            $this->addSql('CREATE TABLE module (
                id SERIAL PRIMARY KEY,
                subchapter_id INT NOT NULL,
                title VARCHAR(512) NOT NULL,
                chapter_id INT NOT NULL,
                bloom_level VARCHAR(32) NOT NULL,
                difficulty VARCHAR(32) NOT NULL,
                h5p_type VARCHAR(64) NOT NULL,
                content TEXT NOT NULL,
                path_id INT DEFAULT NULL,
                created_at TIMESTAMP(0) WITHOUT TIME ZONE NOT NULL,
                CONSTRAINT fk_module_subchapter FOREIGN KEY (subchapter_id) REFERENCES subchapter (id) ON DELETE CASCADE,
                CONSTRAINT fk_module_chapter FOREIGN KEY (chapter_id) REFERENCES chapter (id) ON DELETE CASCADE,
                CONSTRAINT fk_module_path FOREIGN KEY (path_id) REFERENCES learning_path (id) ON DELETE SET NULL
            )');
            $this->addSql('CREATE INDEX idx_module_subchapter ON module (subchapter_id)');
            $this->addSql('CREATE INDEX idx_module_chapter ON module (chapter_id)');
            $this->addSql('CREATE INDEX idx_module_path ON module (path_id)');
        }
    }

    public function down(Schema $schema): void
    {
        $this->addSql('DROP TABLE IF EXISTS module');
        $this->addSql('DROP TABLE IF EXISTS learning_path');
    }
}
