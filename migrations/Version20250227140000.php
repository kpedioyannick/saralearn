<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20250227140000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Rename learning_path.type to learning_path.types.';
    }

    public function up(Schema $schema): void
    {
        $this->addSql('ALTER TABLE learning_path RENAME COLUMN type TO types');
    }

    public function down(Schema $schema): void
    {
        $this->addSql('ALTER TABLE learning_path RENAME COLUMN types TO type');
    }
}
