<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Platforms\SQLitePlatform;
use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20250227160000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Add course (JSON) and mindmap (JSON) to chapter and subchapter.';
    }

    public function up(Schema $schema): void
    {
        $isSqlite = $this->connection->getDatabasePlatform() instanceof SQLitePlatform;
        $jsonType = $isSqlite ? 'TEXT' : 'JSONB';

        $this->addSql(sprintf('ALTER TABLE chapter ADD COLUMN course %s DEFAULT NULL', $jsonType));
        $this->addSql(sprintf('ALTER TABLE chapter ADD COLUMN mindmap %s DEFAULT NULL', $jsonType));
        $this->addSql(sprintf('ALTER TABLE subchapter ADD COLUMN course %s DEFAULT NULL', $jsonType));
        $this->addSql(sprintf('ALTER TABLE subchapter ADD COLUMN mindmap %s DEFAULT NULL', $jsonType));
    }

    public function down(Schema $schema): void
    {
        $isSqlite = $this->connection->getDatabasePlatform() instanceof SQLitePlatform;
        if ($isSqlite) {
            return;
        }
        $this->addSql('ALTER TABLE chapter DROP COLUMN course');
        $this->addSql('ALTER TABLE chapter DROP COLUMN mindmap');
        $this->addSql('ALTER TABLE subchapter DROP COLUMN course');
        $this->addSql('ALTER TABLE subchapter DROP COLUMN mindmap');
    }
}
