"""Regression tests for readonly_sqlite helper."""
import unittest
import sqlite3
import tempfile
import os
import shutil

class TestReadonlySqlite(unittest.TestCase):
    def test_readonly_sqlite_connection(self):
        """Test that readonly_sqlite returns a valid connection."""
        from common import readonly_sqlite
        # Create a temporary database
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, 'test.db')
        # Create a simple database with a table
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE test (id INTEGER PRIMARY KEY)')
        conn.commit()
        conn.close()
        try:
            ro_conn = readonly_sqlite(db_path)
            self.assertIsInstance(ro_conn, sqlite3.Connection)
            # Ensure it's read-only by checking mode? Not directly.
            # Try to insert and expect error
            with self.assertRaises(sqlite3.OperationalError):
                ro_conn.execute('INSERT INTO test (id) VALUES (1)')
            ro_conn.close()
        finally:
            # Clean up
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(tmpdir)

    def test_readonly_sqlite_missing_file(self):
        """Test that readonly_sqlite raises OperationalError for missing file."""
        from common import readonly_sqlite
        with self.assertRaises(sqlite3.OperationalError):
            readonly_sqlite('/non/existent/db.sqlite')

    def test_readonly_sqlite_special_characters(self):
        """Test that readonly_sqlite works with filenames containing special characters."""
        from common import readonly_sqlite
        tmpdir = tempfile.mkdtemp()
        # Create a filename with spaces, unicode, #, ?, &, %
        special_name = 'test db #?% & unicode: café.db'
        db_path = os.path.join(tmpdir, special_name)
        # Create a simple database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE test (id INTEGER PRIMARY KEY)')
        conn.commit()
        conn.close()
        try:
            ro_conn = readonly_sqlite(db_path)
            self.assertIsInstance(ro_conn, sqlite3.Connection)
            # Should be able to read
            rows = ro_conn.execute('SELECT * FROM test').fetchall()
            ro_conn.close()
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(tmpdir)

if __name__ == '__main__':
    unittest.main()