"""Standard-library unittest regressions for the hardened compact_search.inflate decoder."""
import hashlib
import json
import math
import os
import sqlite3
import tempfile
import unittest
import zlib

import compact_search
from compact_search import MAX_BLOCK, MAX_COMPRESSED, inflate, search, source, group_sources
from common import norm


def make_block(obj):
    """Return (zlib payload, sha256 hex) for a JSON-serializable block object."""
    raw = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    return zlib.compress(raw), hashlib.sha256(raw).hexdigest()


def make_db(path, blocks, metadata=(), categories=(), cities=()):
    """Build a read-compatible shard DB: blocks is {block_id: [ (ordinal, lat, lon, name_key, record), ... ]}."""
    db = sqlite3.connect(str(path))
    db.execute('CREATE TABLE grid(gy INTEGER, gx INTEGER, block INTEGER)')
    db.execute('CREATE TABLE block(id INTEGER PRIMARY KEY, payload BLOB, sha256 TEXT)')
    db.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT)')
    db.execute('CREATE TABLE category(category TEXT, block INTEGER)')
    db.execute('CREATE TABLE city(city TEXT, block INTEGER)')
    for block_id, rows in blocks.items():
        payload, sha = make_block(rows)
        db.execute('INSERT INTO block VALUES (?,?,?)', (block_id, payload, sha))
        for _, lat, lon, _, _ in rows:
            db.execute('INSERT INTO grid VALUES (?,?,?)', (math.floor((lat + 90) * 10), math.floor((lon + 180) * 10), block_id))
    for key, value in metadata:
        db.execute('INSERT INTO metadata VALUES (?,?)', (key, json.dumps(value)))
    for category, block_id in categories:
        db.execute('INSERT INTO category VALUES (?,?)', (category, block_id))
    for city, block_id in cities:
        db.execute('INSERT INTO city VALUES (?,?)', (city, block_id))
    db.commit()
    db.close()


RECORD = {
    'id': 'r1',
    'names': {'primary': 'Café 東京 ☕'},
    'basic_category': 'cafe',
    'addresses': [{'locality': 'New York', 'country': 'US'}],
    'confidence': 0.9,
    'operating_status': 'open',
}


class InflateBoundConstantTests(unittest.TestCase):
    def test_max_compressed_is_one_mib(self):
        self.assertEqual(MAX_COMPRESSED, 1024 * 1024)

    def test_max_block_is_32_mib(self):
        self.assertEqual(MAX_BLOCK, 32 * 1024 * 1024)


class InflateValidTests(unittest.TestCase):
    def test_valid_block_round_trip(self):
        obj = [[0, 40.0, -73.0, 'cafe test', RECORD]]
        payload, sha = make_block(obj)
        self.assertEqual(inflate(payload, sha), obj)

    def test_unicode_json_round_trip(self):
        obj = [[0, 40.0, -73.0, norm('Café 東京 ☕'), RECORD]]
        payload, sha = make_block(obj)
        self.assertEqual(inflate(payload, sha), obj)
        self.assertEqual(inflate(payload, sha)[0][4]['names']['primary'], 'Café 東京 ☕')

    def test_bytearray_and_memoryview_accepted(self):
        obj = [[0, 1.0, 2.0, 'k', RECORD]]
        payload, sha = make_block(obj)
        self.assertEqual(inflate(bytearray(payload), sha), obj)
        self.assertEqual(inflate(memoryview(payload), sha), obj)

    def test_exactly_max_block_still_valid(self):
        # A block whose inflated size is exactly MAX_BLOCK was valid before and must stay valid.
        base = len(json.dumps({'pad': ''}, ensure_ascii=False).encode('utf-8'))
        obj = {'pad': 'a' * (MAX_BLOCK - base)}
        raw = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.assertEqual(len(raw), MAX_BLOCK)
        payload = zlib.compress(raw)
        self.assertEqual(inflate(payload, hashlib.sha256(raw).hexdigest()), obj)


class InflateRejectionTests(unittest.TestCase):
    def test_compressed_bound_checked_before_decoding(self):
        # Not valid zlib at all: must fail the pre-decode bound with ValueError, not zlib.error.
        with self.assertRaises(ValueError):
            inflate(b'x' * (MAX_COMPRESSED + 1), '0' * 64)

    def test_compressed_bound_boundary(self):
        payload, sha = make_block({'ok': True})
        old = compact_search.MAX_COMPRESSED
        self.addCleanup(lambda: setattr(compact_search, 'MAX_COMPRESSED', old))
        compact_search.MAX_COMPRESSED = len(payload)
        self.assertEqual(inflate(payload, sha), {'ok': True})
        compact_search.MAX_COMPRESSED = len(payload) - 1
        with self.assertRaises(ValueError):
            inflate(payload, sha)

    def test_oversized_compressed_payload(self):
        payload = zlib.compress(os.urandom(MAX_COMPRESSED + 64))
        self.assertGreater(len(payload), MAX_COMPRESSED)
        with self.assertRaises(ValueError):
            inflate(payload, '0' * 64)

    def test_corrupt_zlib_raises_value_error(self):
        obj = [(0, 40.0, -73.0, 'k', dict(RECORD, note='x' * 2000))]
        payload, sha = make_block(obj)
        mid = len(payload) // 2
        variants = [
            b'\x00\x00' + payload[2:],                       # bad header
            payload[:-4] + b'\x00\x00\x00\x00',              # bad adler checksum
            payload[:mid] + b'\xff' * 8 + payload[mid + 8:], # corrupted body
        ]
        for bad in variants:
            with self.assertRaises(ValueError):
                inflate(bad, sha)

    def test_truncated_zlib(self):
        payload, sha = make_block([(0, 40.0, -73.0, 'k', RECORD)])
        for cut in (1, 2, len(payload) - 5, len(payload) - 1):
            with self.assertRaises(ValueError):
                inflate(payload[:cut], sha)

    def test_trailing_garbage(self):
        payload, sha = make_block({'ok': True})
        with self.assertRaises(ValueError):
            inflate(payload + b'garbage', sha)

    def test_concatenated_streams(self):
        payload, sha = make_block({'ok': True})
        with self.assertRaises(ValueError):
            inflate(payload + payload, sha)

    def test_wrong_sha256(self):
        payload, _ = make_block({'ok': True})
        with self.assertRaises(ValueError):
            inflate(payload, '0' * 64)

    def test_invalid_json(self):
        for bad in (b'not json', b'[1, 2,', b'\xff\xfe\x00json', b''):
            payload = zlib.compress(bad)
            with self.assertRaises(ValueError):
                inflate(payload, hashlib.sha256(bad).hexdigest())

    def test_inflated_bound_enforced(self):
        raw = b'\x00' * (MAX_BLOCK + 16)
        payload = zlib.compress(raw)
        self.assertLess(len(payload), MAX_COMPRESSED)
        with self.assertRaises(ValueError):
            inflate(payload, hashlib.sha256(raw).hexdigest())

    def test_empty_payload(self):
        with self.assertRaises(ValueError):
            inflate(b'', '0' * 64)

    def test_non_bytes_payload(self):
        with self.assertRaises(ValueError):
            inflate('nope', '0' * 64)


class InflateEndToEndTests(unittest.TestCase):
    """Valid results must be unchanged through the real search/source/group_sources paths."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_path = os.path.join(self._tmp.name, 'shard.db')
        rows = [[0, 40.0, -73.0, norm('Café 東京 ☕'), RECORD]]
        make_db(self.db_path, {1: rows}, metadata=[('release', '2026-09-23')],
                categories=[('cafe', 1)], cities=[('New York', 1)])

    def test_search_returns_valid_row(self):
        rows = search([self.db_path], 40.0, -73.0, radius_km=10)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['id'], 'r1')
        self.assertEqual(row['name'], 'Café 東京 ☕')
        self.assertEqual(row['category'], 'cafe')
        self.assertEqual(row['city'], 'New York')
        self.assertEqual(row['country'], 'US')
        self.assertEqual(row['block_id'], 1)
        self.assertEqual(row['source_ordinal'], 0)
        self.assertEqual(row['distance_km'], 0.0)
        self.assertIsNone(row['live_status'])

    def test_search_with_category_filter(self):
        self.assertEqual(len(search([self.db_path], 40.0, -73.0, category='cafe')), 1)
        self.assertEqual(search([self.db_path], 40.0, -73.0, category='bakery'), [])

    def test_source_returns_record_and_provenance(self):
        got = source(self.db_path, 1, 0, 'r1')
        self.assertIsNotNone(got)
        self.assertEqual(got['record'], RECORD)
        self.assertEqual(got['latitude'], 40.0)
        self.assertEqual(got['longitude'], -73.0)
        self.assertEqual(got['row_ordinal'], 0)
        self.assertEqual(got['provenance'], {'release': '2026-09-23'})
        self.assertIsNone(source(self.db_path, 1, 0, 'other'))

    def test_group_sources_yields_variant(self):
        variants = list(group_sources([self.db_path], 'Café 東京 ☕', 40.0, -73.0, 'cafe'))
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0]['id'], 'r1')
        self.assertEqual(variants[0]['block_id'], 1)
        self.assertEqual(variants[0]['source_ordinal'], 0)

    def test_corrupt_block_in_db_raises_value_error(self):
        db = sqlite3.connect(str(self.db_path))
        payload, _ = db.execute('SELECT payload, sha256 FROM block WHERE id=1').fetchone()
        db.execute('UPDATE block SET payload=? WHERE id=1', (b'\x00\x00' + payload[2:],))
        db.commit()
        db.close()
        with self.assertRaises(ValueError):
            search([self.db_path], 40.0, -73.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
