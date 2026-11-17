import unittest
import tempfile
import os
import json
import threading
from common import atomic_json

class TestAtomicJson(unittest.TestCase):
    def test_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test.json')
            obj = {'a': 1, 'b': [2, 3]}
            atomic_json(path, obj)
            with open(path, 'r') as f:
                data = json.load(f)
            self.assertEqual(data, obj)
    
    def test_failure_cleanup_before_replacement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test.json')
            # Create original file with content
            with open(path, 'w') as f:
                f.write('original')
            # Try to write a non-serializable object, should raise TypeError
            with self.assertRaises(TypeError):
                atomic_json(path, set([1, 2]))
            # Original file should still exist with original content
            with open(path, 'r') as f:
                self.assertEqual(f.read(), 'original')
            # No temporary file should remain
            tmp_files = [f for f in os.listdir(tmpdir) if f.endswith('.tmp')]
            self.assertEqual(tmp_files, [])
    
    def test_failure_cleanup_on_replace_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test.json')
            obj = {'a': 1}
            # Mock Path.replace to raise an exception
            original_replace = __import__('pathlib').Path.replace
            def mock_replace(self, other):
                raise OSError('mock replace error')
            __import__('pathlib').Path.replace = mock_replace
            try:
                with self.assertRaises(OSError):
                    atomic_json(path, obj)
            finally:
                # Restore original replace
                __import__('pathlib').Path.replace = original_replace
            # Original file should not exist because we didn't create it
            self.assertFalse(os.path.exists(path))
            # No temporary file should remain
            tmp_files = [f for f in os.listdir(tmpdir) if f.endswith('.tmp')]
            self.assertEqual(tmp_files, [])
    
    def test_concurrency(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test.json')
            written_ids = set()
            def writer(i):
                obj = {'id': i}
                written_ids.add(i)
                atomic_json(path, obj)
            threads = []
            for i in range(10):
                t = threading.Thread(target=writer, args=(i,))
                threads.append(t)
                t.start()
            for t in threads:
                t.join()
            # Read final file
            with open(path, 'r') as f:
                data = json.load(f)
            # The final data should be one of the written objects
            self.assertIn(data['id'], written_ids)
            # Also ensure the file is valid JSON
            self.assertIsInstance(data, dict)
            self.assertIn('id', data)

if __name__ == '__main__':
    unittest.main()