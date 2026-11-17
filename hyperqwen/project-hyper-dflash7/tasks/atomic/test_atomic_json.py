"""Standard-library regressions for common.atomic_json.

Covers: exact JSON publication, atomic overwrite, failure cleanup (destination
bytes preserved, only this call's temp removed, unrelated files untouched), and
concurrent writers (threads and processes) never publishing torn/partial JSON.
"""
import hashlib
import json
import multiprocessing as mp
import os
import pathlib
import tempfile
import threading
import unittest
from unittest import mock

from common import atomic_json, file_sha256, norm


def _process_writer(dest, writer, rounds):
    for r in range(rounds):
        atomic_json(dest, {'writer': writer, 'round': r, 'payload': 'x' * (64 + 11 * ((writer + r) % 17))})


class AtomicJsonTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)
        self.dest = self.dir / 'evidence.json'
        self.unrelated = self.dir / 'unrelated.txt'
        self.unrelated.write_text('do not touch\n', encoding='utf-8')

    def tearDown(self):
        self._tmp.cleanup()

    def _leftover_tmps(self):
        return sorted(p.name for p in self.dir.iterdir() if p.name.endswith('.tmp'))

    def _assert_destination_intact(self, expected_bytes):
        self.assertEqual(self.dest.read_bytes(), expected_bytes)
        self.assertEqual(self.unrelated.read_text(encoding='utf-8'), 'do not touch\n')
        self.assertEqual(self._leftover_tmps(), [])

    def test_write_publishes_exact_json(self):
        obj = {'name': 'Café ☕', 'nested': {'a': [1, 2.5, None]}, 'note': 'line\nbreak'}
        atomic_json(self.dest, obj)
        self.assertEqual(self.dest.read_bytes(), (json.dumps(obj, indent=2) + '\n').encode('utf-8'))
        self.assertEqual(json.loads(self.dest.read_text(encoding='utf-8')), obj)
        self.assertEqual(file_sha256(self.dest), hashlib.sha256(self.dest.read_bytes()).hexdigest())
        self.assertEqual(self._leftover_tmps(), [])

    def test_overwrite_replaces_previous_bytes(self):
        atomic_json(self.dest, {'v': 1})
        first = self.dest.read_bytes()
        atomic_json(self.dest, {'v': 2, 'pad': 'z' * 500})
        self.assertEqual(self.dest.read_bytes(), (json.dumps({'v': 2, 'pad': 'z' * 500}, indent=2) + '\n').encode('utf-8'))
        self.assertNotEqual(self.dest.read_bytes(), first)
        self.assertEqual(self._leftover_tmps(), [])

    def test_norm_and_file_sha256_preserved(self):
        self.assertEqual(norm('  Héllo,  Wörld '), 'héllo, wörld')
        self.assertEqual(norm('ﬁle  name'), 'file name')
        payload = b'abc\ndef\n'
        f = self.dir / 'hash.bin'
        f.write_bytes(payload)
        self.assertEqual(file_sha256(f), hashlib.sha256(payload).hexdigest())

    def test_unserializable_object_preserves_destination(self):
        atomic_json(self.dest, {'v': 'original'})
        before = self.dest.read_bytes()
        with self.assertRaises(TypeError):
            atomic_json(self.dest, {'v': object()})
        self._assert_destination_intact(before)

    def test_write_failure_preserves_destination_and_cleans_tmp(self):
        atomic_json(self.dest, {'v': 'original', 'pad': 'y' * 300})
        before = self.dest.read_bytes()
        real_fdopen = os.fdopen

        class _FailingWriter:
            def __init__(self, real):
                self.real = real

            def write(self, data):
                raise OSError('simulated write failure')

            def flush(self):
                pass

            def fileno(self):
                return self.real.fileno()

            def close(self):
                self.real.close()

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.close()

        with mock.patch('os.fdopen', side_effect=lambda fd, *a, **k: _FailingWriter(real_fdopen(fd, 'wb'))):
            with self.assertRaises(OSError):
                atomic_json(self.dest, {'v': 'new'})
        self._assert_destination_intact(before)

    def test_fsync_failure_preserves_destination_and_cleans_tmp(self):
        atomic_json(self.dest, {'v': 'original'})
        before = self.dest.read_bytes()
        with mock.patch('os.fsync', side_effect=OSError('simulated fsync failure')):
            with self.assertRaises(OSError):
                atomic_json(self.dest, {'v': 'new'})
        self._assert_destination_intact(before)

    def test_replace_failure_preserves_destination_and_cleans_tmp(self):
        atomic_json(self.dest, {'v': 'original'})
        before = self.dest.read_bytes()
        with mock.patch.object(pathlib.Path, 'replace', side_effect=OSError('simulated rename failure')):
            with self.assertRaises(OSError):
                atomic_json(self.dest, {'v': 'new'})
        self._assert_destination_intact(before)

    def test_mkstemp_failure_preserves_destination_and_cleans_tmp(self):
        atomic_json(self.dest, {'v': 'original'})
        before = self.dest.read_bytes()
        with mock.patch('tempfile.mkstemp', side_effect=OSError('simulated temp failure')):
            with self.assertRaises(OSError):
                atomic_json(self.dest, {'v': 'new'})
        self._assert_destination_intact(before)

    def test_concurrent_thread_writers_publish_complete_json(self):
        writers, rounds = 8, 25
        errors = []
        lock = threading.Lock()

        def worker(i):
            for r in range(rounds):
                try:
                    atomic_json(self.dest, {'writer': i, 'round': r, 'payload': 'x' * (100 + 7 * ((i + r) % 13))})
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(writers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        text = self.dest.read_text(encoding='utf-8')
        obj = json.loads(text)  # must be complete, valid JSON
        self.assertEqual(text, json.dumps(obj, indent=2) + '\n')  # exactly one writer's full payload
        self.assertIn(obj['writer'], range(writers))
        self.assertIn(obj['round'], range(rounds))
        self.assertEqual(self._leftover_tmps(), [])

    def test_concurrent_process_writers_publish_complete_json(self):
        if 'fork' not in mp.get_all_start_methods():
            self.skipTest('fork start method unavailable')
        writers, rounds = 4, 10
        with mp.get_context('fork').Pool(writers) as pool:
            pool.starmap(_process_writer, [(str(self.dest), i, rounds) for i in range(writers)])
        text = self.dest.read_text(encoding='utf-8')
        obj = json.loads(text)
        self.assertEqual(text, json.dumps(obj, indent=2) + '\n')
        self.assertIn(obj['writer'], range(writers))
        self.assertIn(obj['round'], range(rounds))
        self.assertEqual(self._leftover_tmps(), [])

    def test_missing_parent_directory_fails_without_side_effects(self):
        missing = self.dir / 'no_such_dir' / 'evidence.json'
        with self.assertRaises(FileNotFoundError):
            atomic_json(missing, {'v': 1})
        self.assertFalse((self.dir / 'no_such_dir').exists())
        self.assertEqual(self._leftover_tmps(), [])


if __name__ == '__main__':
    unittest.main()
