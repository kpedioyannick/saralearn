<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20250227170000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Add course_music table for Suno-generated music per subchapter.';
    }

    public function up(Schema $schema): void
    {
        $table = $schema->createTable('course_music');
        $table->addColumn('id', 'integer', ['autoincrement' => true, 'notnull' => true]);
        $table->addColumn('subchapter_id', 'integer', ['notnull' => true]);
        $table->addColumn('suno_task_id', 'string', ['length' => 255, 'notnull' => false]);
        $table->addColumn('audio_url', 'string', ['length' => 2048, 'notnull' => false]);
        $table->addColumn('prompt', 'text', ['notnull' => false]);
        $table->addColumn('title', 'string', ['length' => 255, 'notnull' => false]);
        $table->addColumn('duration', 'float', ['notnull' => false]);
        $table->addColumn('created_at', 'datetime_immutable', ['notnull' => true]);
        $table->setPrimaryKey(['id']);
        $table->addIndex(['subchapter_id'], 'IDX_course_music_subchapter');
        $table->addForeignKeyConstraint('subchapter', ['subchapter_id'], ['id'], ['onDelete' => 'CASCADE'], 'FK_course_music_subchapter');
    }

    public function down(Schema $schema): void
    {
        $schema->dropTable('course_music');
    }
}
