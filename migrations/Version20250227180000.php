<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20250227180000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Add app_user (learners) and learning_path_learner (Path ManyToMany with User).';
    }

    public function up(Schema $schema): void
    {
        $user = $schema->createTable('app_user');
        $user->addColumn('id', 'integer', ['autoincrement' => true, 'notnull' => true]);
        $user->addColumn('email', 'string', ['length' => 180, 'notnull' => true]);
        $user->addColumn('display_name', 'string', ['length' => 255, 'notnull' => false]);
        $user->addColumn('created_at', 'datetime_immutable', ['notnull' => true]);
        $user->setPrimaryKey(['id']);
        $user->addUniqueIndex(['email'], 'UNIQ_app_user_email');

        $join = $schema->createTable('learning_path_learner');
        $join->addColumn('learning_path_id', 'integer', ['notnull' => true]);
        $join->addColumn('user_id', 'integer', ['notnull' => true]);
        $join->setPrimaryKey(['learning_path_id', 'user_id']);
        $join->addForeignKeyConstraint('learning_path', ['learning_path_id'], ['id'], ['onDelete' => 'CASCADE'], 'FK_learning_path_learner_path');
        $join->addForeignKeyConstraint('app_user', ['user_id'], ['id'], ['onDelete' => 'CASCADE'], 'FK_learning_path_learner_user');
        $join->addIndex(['user_id'], 'IDX_learning_path_learner_user');
    }

    public function down(Schema $schema): void
    {
        $schema->dropTable('learning_path_learner');
        $schema->dropTable('app_user');
    }
}
