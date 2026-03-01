<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Platforms\SQLitePlatform;
use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20250227150000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Change learning_path.types from VARCHAR to JSON (array of Bloom levels).';
    }

    public function up(Schema $schema): void
    {
        $isSqlite = $this->connection->getDatabasePlatform() instanceof SQLitePlatform;

        if ($isSqlite) {
            $rows = $this->connection->fetchAllAssociative('SELECT id, types FROM learning_path WHERE types IS NOT NULL');
            foreach ($rows as $row) {
                $types = $this->stringToArray((string) $row['types']);
                $this->connection->update(
                    'learning_path',
                    ['types' => json_encode($types, \JSON_THROW_ON_ERROR)],
                    ['id' => $row['id']],
                    ['types' => 'string', 'id' => 'integer'],
                );
            }
        } else {
            $this->addSql(<<<'SQL'
                ALTER TABLE learning_path
                ALTER COLUMN types TYPE JSONB
                USING (
                    CASE
                        WHEN types IS NULL OR trim(types) = '' THEN NULL
                        ELSE to_jsonb(ARRAY(SELECT trim(unnest(string_to_array(types, ',')))))
                    END
                )
            SQL);
        }
    }

    public function down(Schema $schema): void
    {
        $isSqlite = $this->connection->getDatabasePlatform() instanceof SQLitePlatform;

        if ($isSqlite) {
            $rows = $this->connection->fetchAllAssociative('SELECT id, types FROM learning_path WHERE types IS NOT NULL');
            foreach ($rows as $row) {
                $decoded = json_decode((string) $row['types'], true, 512, \JSON_THROW_ON_ERROR);
                $str = is_array($decoded) ? implode(',', $decoded) : (string) $row['types'];
                $this->connection->update(
                    'learning_path',
                    ['types' => $str],
                    ['id' => $row['id']],
                    ['types' => 'string', 'id' => 'integer'],
                );
            }
        } else {
            $this->addSql("ALTER TABLE learning_path ALTER COLUMN types TYPE VARCHAR(64) USING array_to_string(ARRAY(SELECT jsonb_array_elements_text(types)), ',')");
        }
    }

    /**
     * @return list<string>
     */
    private function stringToArray(string $value): array
    {
        if ($value === '') {
            return [];
        }
        $decoded = json_decode($value, true);
        if (is_array($decoded)) {
            return array_values(array_filter(array_map('trim', $decoded)));
        }
        return array_values(array_filter(array_map('trim', explode(',', $value))));
    }
}
