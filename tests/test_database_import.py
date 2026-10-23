"""Real PostgreSQL tests. Requires F1_TEST_ADMIN_DSN and F1_TEST_DATA_DIR.
Creates and removes two dedicated databases; never uses the project database.
Run: python -m unittest discover -s tests -v
"""
import csv
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import uuid

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import parse_dsn, make_dsn

from database_import import import_dataset


@unittest.skipUnless(os.getenv('F1_TEST_ADMIN_DSN') and os.getenv('F1_TEST_DATA_DIR'),
                     'Set test admin DSN and Kaggle data directory')
class ImportIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_dsn = os.environ['F1_TEST_ADMIN_DSN']
        cls.data = Path(os.environ['F1_TEST_DATA_DIR']).resolve()
        cls.names = ['f1_test_' + uuid.uuid4().hex[:12] for _ in range(2)]
        cls.admin = psycopg2.connect(cls.admin_dsn)
        cls.admin.autocommit = True
        cls.connections = []
        for name in cls.names:
            with cls.admin.cursor() as cur:
                cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
            opts = parse_dsn(cls.admin_dsn)
            opts['dbname'] = name
            cls.connections.append(psycopg2.connect(make_dsn(**opts)))
        cls.loaded, cls.fresh = cls.connections
        cls.report = import_dataset(cls.loaded, cls.data)

    @classmethod
    def tearDownClass(cls):
        for conn in cls.connections:
            conn.close()
        with cls.admin.cursor() as cur:
            for name in cls.names:
                cur.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
        cls.admin.close()

    def test_existing_project_entry_points(self):
        from main import commit_schema, insert_data
        commit_schema(self.loaded)
        commit_schema(self.loaded)
        self.assertTrue(insert_data(self.loaded, self.data)['skipped'])

    def test_counts_and_repeat_startup(self):
        self.assertFalse(self.report['skipped'])
        self.assertTrue(import_dataset(self.loaded, self.data)['skipped'])
        self.assertGreater(self.report['counts']['lap_times'], 500000)

    def test_query_and_duration_mapping(self):
        with self.loaded:
            with self.loaded.cursor() as cur:
                cur.execute('''SELECT extract(epoch FROM p.duration) * 1000
                    FROM pit_stops p JOIN results r USING (result_id)
                    WHERE r.race_id=841 AND r.driver_id=153 AND p.stop=1''')
                self.assertEqual(int(cur.fetchone()[0]), 26898)
                cur.execute('''SELECT extract(epoch FROM l.lap_time) * 1000
                    FROM lap_times l JOIN results r USING (result_id)
                    WHERE r.race_id=841 AND r.driver_id=20 AND l.lap=1''')
                self.assertEqual(int(cur.fetchone()[0]), 98109)
                cur.execute('''SELECT d.surname, count(*) FROM drivers d
                    JOIN results r USING (driver_id) WHERE r.position_order=1
                    GROUP BY d.driver_id ORDER BY count(*) DESC LIMIT 10''')
                self.assertEqual(len(cur.fetchall()), 10)
                cur.execute('''SELECT d.surname, avg(l.lap_time) FROM lap_times l
                    JOIN results r USING (result_id) JOIN races a USING (race_id)
                    JOIN drivers d USING (driver_id)
                    WHERE a.year=2023 AND a.name='Las Vegas Grand Prix'
                    GROUP BY d.driver_id ORDER BY avg(l.lap_time) LIMIT 1''')
                self.assertIsNotNone(cur.fetchone())
                # Demo DML works, but do not persist synthetic data.
                cur.execute("INSERT INTO statuses VALUES (999999, 'Demo')")
                cur.execute("UPDATE statuses SET status='Updated demo' WHERE status_id=999999")
                cur.execute('DELETE FROM statuses WHERE status_id=999999')
                self.assertEqual(cur.rowcount, 1)

    def test_unmatched_child_rolls_back_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for file in self.data.glob('*.csv'):
                (directory / file.name).symlink_to(file)
            path = directory / 'pit_stops.csv'
            path.unlink()
            with (self.data / path.name).open(newline='') as src, path.open('w', newline='') as dst:
                reader, writer = csv.reader(src), csv.writer(dst)
                writer.writerow(next(reader))
                first = next(reader)
                first[1] = '999999'
                writer.writerow(first)
                writer.writerows(reader)
            with self.assertRaisesRegex(psycopg2.Error, 'missing or ambiguous'):
                import_dataset(self.fresh, directory)
            with self.fresh:
                with self.fresh.cursor() as cur:
                    cur.execute("SELECT to_regclass('public.results')")
                    self.assertIsNone(cur.fetchone()[0])
            with self.assertRaisesRegex(ValueError, 'CSV files or imported row counts changed'):
                import_dataset(self.loaded, directory)


if __name__ == '__main__':
    unittest.main()
