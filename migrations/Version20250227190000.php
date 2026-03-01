<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20250227190000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Add classroom_id to app_user (User ManyToOne Classroom).';
    }

    public function up(Schema $schema): void
    {
        $user = $schema->getTable('app_user');
        $user->addColumn('classroom_id', 'integer', ['notnull' => false]);
        $user->addForeignKeyConstraint('classroom', ['classroom_id'], ['id'], ['onDelete' => 'SET NULL'], 'FK_app_user_classroom');
        $user->addIndex(['classroom_id'], 'IDX_app_user_classroom');
    }

    public function down(Schema $schema): void
    {
        $schema->getTable('app_user')->removeForeignKey('FK_app_user_classroom');
        $schema->getTable('app_user')->dropColumn('classroom_id');
    }
}
