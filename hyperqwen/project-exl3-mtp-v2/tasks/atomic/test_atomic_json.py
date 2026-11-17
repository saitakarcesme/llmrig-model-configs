"""Regression tests for common.atomic_json: unique temp file, atomic publish, cleanup."""
import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import common


class AtomicJsonTests(unittest.TestCase):
  def setUp(self):
    self.dir = Path(tempfile.mkdtemp(prefix='atomic_json_test.'))
    self.dest = self.dir / 'evidence.json'

  def tearDown(self):
    shutil.rmtree(self.dir, ignore_errors=True)

  def tmp_files(self):
    return sorted(p.name for p in self.dir.iterdir() if p.name.endswith('.tmp'))

  # --- public API and content preservation ---

  def test_writes_exact_json_content(self):
    obj = {'name': 'Café Über', 'count': 3, 'nested': {'a': [1, 2, 3]}}
    common.atomic_json(self.dest, obj)
    self.assertEqual(self.dest.read_text(), json.dumps(obj, indent=2) + '\n')
    self.assertEqual(json.loads(self.dest.read_text()), obj)

  def test_accepts_str_and_path_and_overwrites(self):
    common.atomic_json(str(self.dest), {'v': 1})
    self.assertTrue(self.dest.exists())
    common.atomic_json(self.dest, {'v': 2})
    self.assertEqual(json.loads(self.dest.read_text()), {'v': 2})

  def test_norm_and_file_sha256_unchanged(self):
    self.assertEqual(common.norm('Café \tBAR'), 'café bar')
    common.atomic_json(self.dest, {'x': 1})
    self.assertEqual(common.file_sha256(self.dest),
                     hashlib.sha256(self.dest.read_bytes()).hexdigest())

  def test_preserves_existing_destination_mode(self):
    self.dest.write_text('old')
    os.chmod(self.dest, 0o640)
    common.atomic_json(self.dest, {'v': 1})
    self.assertEqual(self.dest.stat().st_mode & 0o7777, 0o640)

  # --- failure semantics: previous bytes preserved, only own tmp removed ---

  def test_replace_failure_preserves_previous_bytes_and_cleans_tmp(self):
    common.atomic_json(self.dest, {'v': 'previous'})
    before = self.dest.read_bytes()
    with mock.patch('os.replace', side_effect=OSError('no space left on device')):
      with self.assertRaises(OSError):
        common.atomic_json(self.dest, {'v': 'next'})
    self.assertEqual(self.dest.read_bytes(), before)
    self.assertEqual(self.tmp_files(), [])

  def test_write_failure_preserves_previous_bytes_and_cleans_tmp(self):
    common.atomic_json(self.dest, {'v': 'previous'})
    before = self.dest.read_bytes()
    with mock.patch('os.fsync', side_effect=OSError('I/O error')):
      with self.assertRaises(OSError):
        common.atomic_json(self.dest, {'v': 'next'})
    self.assertEqual(self.dest.read_bytes(), before)
    self.assertEqual(self.tmp_files(), [])

  def test_fdopen_failure_cleans_tmp_and_creates_nothing(self):
    with mock.patch('os.fdopen', side_effect=OSError('bad file descriptor')):
      with self.assertRaises(OSError):
        common.atomic_json(self.dest, {'v': 'x'})
    self.assertFalse(self.dest.exists())
    self.assertEqual(self.tmp_files(), [])

  def test_failure_leaves_unrelated_files_alone(self):
    common.atomic_json(self.dest, {'v': 'previous'})
    unrelated = self.dir / 'unrelated.txt'
    unrelated.write_text('keep me')
    stale = self.dir / (self.dest.name + '.stale.tmp')
    stale.write_text('stale')
    with mock.patch('os.replace', side_effect=OSError('boom')):
      with self.assertRaises(OSError):
        common.atomic_json(self.dest, {'v': 'next'})
    self.assertEqual(self.dest.read_text(), json.dumps({'v': 'previous'}, indent=2) + '\n')
    self.assertEqual(unrelated.read_text(), 'keep me')
    self.assertTrue(stale.exists())

  def test_success_removes_only_own_tmp(self):
    stale = self.dir / (self.dest.name + '.stale.tmp')
    stale.write_text('stale')
    common.atomic_json(self.dest, {'v': 1})
    self.assertEqual(self.tmp_files(), [stale.name])

  # --- concurrency ---

  def test_concurrent_writers_publish_complete_json(self):
    threads, iters = 8, 20
    payloads = {}
    real_fsync = os.fsync

    def slow_fsync(fd):
      time.sleep(0.001)  # widen the window between write and replace
      real_fsync(fd)

    def worker(i):
      for j in range(iters):
        obj = {'writer': i, 'iteration': j, 'data': ['x' * 64] * 40}
        payloads[(i, j)] = json.dumps(obj, indent=2) + '\n'
        common.atomic_json(self.dest, obj)

    barrier = threading.Barrier(threads)

    def run(i):
      barrier.wait()
      worker(i)

    with mock.patch('os.fsync', side_effect=slow_fsync):
      ts = [threading.Thread(target=run, args=(i,)) for i in range(threads)]
      for t in ts:
        t.start()
      for t in ts:
        t.join()
    final = self.dest.read_text()
    self.assertIn(final, payloads.values())  # exactly one complete payload, no interleaving
    json.loads(final)  # must be valid JSON
    self.assertEqual(self.tmp_files(), [])

  def test_concurrent_distinct_destinations_do_not_interfere(self):
    def worker(i):
      for j in range(10):
        common.atomic_json(self.dir / ('w%d.json' % i), {'writer': i, 'iteration': j})

    ts = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in ts:
      t.start()
    for t in ts:
      t.join()
    for i in range(8):
      self.assertEqual(json.loads((self.dir / ('w%d.json' % i)).read_text()),
                       {'writer': i, 'iteration': 9})
    self.assertEqual(self.tmp_files(), [])


if __name__ == '__main__':
  unittest.main()
