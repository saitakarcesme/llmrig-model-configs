"""Regression tests: read-only SQLite access for filenames with spaces, Unicode, #, ?, & and %."""
import hashlib
import json
import math
import os
import pathlib
import sqlite3
import tempfile
import unittest
import uuid
import zlib

import catalog
import common
import compact_search
import enrich
import search

LAT, LON = 40.7128, -74.0060

SPECIAL_NAMES = [
    'plain.sqlite',
    'with space.sqlite',
    'café 数据库.sqlite',
    'hash#tag.sqlite',
    'question?mark.sqlite',
    'amp&ersand.sqlite',
    'percent%20and%zz.sqlite',
    'combo # ? & % ünïcode.sqlite',
]


def _zlib(data):
    return zlib.compress(data)


def make_places_db(path):
    """Schema-v1 place shard consumed by search.py."""
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE place (id BLOB PRIMARY KEY, name TEXT, name_key TEXT, lat REAL, lon REAL,'
               ' category TEXT, city TEXT, country TEXT, confidence REAL, status TEXT, entity_key BLOB,'
               ' gy INTEGER, gx INTEGER, ordinal INTEGER, detail BLOB)')
    db.execute('CREATE TABLE category (place_id BLOB, category TEXT)')
    db.execute('CREATE TABLE progress (key TEXT PRIMARY KEY, value TEXT)')
    db.execute('CREATE TABLE conflict (id BLOB, ordinal INTEGER, detail BLOB)')
    pid, entity = uuid.uuid4().bytes, uuid.uuid4().bytes
    detail = {'id': 'p1', 'name': 'Test Cafe', 'lat': LAT, 'lon': LON, 'category': 'cafe'}
    db.execute('INSERT INTO place VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
               (pid, 'Test Cafe', common.norm('Test Cafe'), LAT, LON, 'cafe', 'New York', 'US',
                0.9, 'operating', entity,
                math.floor((LAT + 90) * 100), math.floor((LON + 180) * 100), 7,
                _zlib(json.dumps(detail).encode())))
    db.execute('INSERT INTO category VALUES (?,?)', (pid, 'cafe'))
    for key, value in [('release', '2026-09-23.1'), ('source', 'places.parquet'),
                       ('source_sha256', 'abc123'), ('schema_version', '1')]:
        db.execute('INSERT INTO progress VALUES (?,?)', (key, json.dumps(value)))
    db.execute('INSERT INTO conflict VALUES (?,?,?)',
               (pid, 1, _zlib(json.dumps({'id': 'p1', 'note': 'conflict'}).encode())))
    db.commit()
    db.close()


def make_compact_db(path):
    """Schema-v2 block shard consumed by compact_search.py."""
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE grid (block INTEGER, gy INTEGER, gx INTEGER)')
    db.execute('CREATE TABLE block (id INTEGER PRIMARY KEY, payload BLOB, sha256 TEXT)')
    db.execute('CREATE TABLE category (block INTEGER, category TEXT)')
    db.execute('CREATE TABLE city (block INTEGER, city TEXT)')
    db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)')
    record = {
        'id': 'c1',
        'names': {'primary': 'Compact Cafe'},
        'taxonomy': {'primary': 'cafe', 'hierarchy': ['cafe'], 'alternates': []},
        'basic_category': 'cafe',
        'addresses': [{'locality': 'New York', 'country': 'US'}],
        'confidence': 0.9,
        'operating_status': 'operating',
    }
    raw = json.dumps([[0, LAT, LON, common.norm('Compact Cafe'), record]]).encode()
    db.execute('INSERT INTO grid VALUES (?,?,?)',
               (1, math.floor((LAT + 90) * 10), math.floor((LON + 180) * 10)))
    db.execute('INSERT INTO category VALUES (?,?)', (1, 'cafe'))
    db.execute('INSERT INTO city VALUES (?,?)', (1, 'New York'))
    db.execute('INSERT INTO block VALUES (?,?,?)', (1, _zlib(raw), hashlib.sha256(raw).hexdigest()))
    for key, value in [('release', '2026-09-23.1'), ('schema_version', '2')]:
        db.execute('INSERT INTO metadata VALUES (?,?)', (key, json.dumps(value)))
    db.commit()
    db.close()


def make_city_db(path):
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE city (id INTEGER PRIMARY KEY, name TEXT, population INTEGER)')
    db.execute('CREATE TABLE alias (name_key TEXT, city_id INTEGER)')
    db.execute('INSERT INTO city VALUES (1,"New York",8000000)')
    db.execute('INSERT INTO alias VALUES (?,1)', (common.norm('New York'),))
    db.commit()
    db.close()


def make_osm_db(path, compact=False):
    """OSM enrichment shard; compact=True uses the block/slot layout."""
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE snapshot (sha256 TEXT)')
    db.execute('INSERT INTO snapshot VALUES (?)', ('snapshot-sha',))
    if compact:
        db.execute('CREATE TABLE osm (id INTEGER PRIMARY KEY, name_key TEXT, type TEXT, lat REAL, lon REAL,'
                   ' vegan TEXT, vegetarian TEXT, block INTEGER, slot INTEGER)')
        db.execute('CREATE TABLE block (id INTEGER PRIMARY KEY, payload BLOB, sha256 TEXT)')
        raw = {'id': 456, 'type': 'node', 'version': 1,
               'tags': {'name': 'Compact Cafe', 'diet:vegan': 'yes', 'diet:vegetarian': 'yes',
                        'opening_hours': '24/7'}}
        payload = json.dumps([[LAT, LON, raw]]).encode()
        db.execute('INSERT INTO block VALUES (?,?,?)', (1, _zlib(payload), hashlib.sha256(payload).hexdigest()))
        db.execute('INSERT INTO osm VALUES (?,?,?,?,?,?,?,?,?)',
                   (456, common.norm('Compact Cafe'), 'node', LAT, LON, 'yes', 'yes', 1, 0))
    else:
        db.execute('CREATE TABLE osm (id INTEGER PRIMARY KEY, name TEXT, name_key TEXT, type TEXT, lat REAL,'
                   ' lon REAL, vegan TEXT, vegetarian TEXT, raw BLOB)')
        raw = {'id': 123, 'type': 'node', 'version': 3,
               'tags': {'name': 'Compact Cafe', 'diet:vegan': 'yes', 'diet:vegetarian': 'yes',
                        'opening_hours': '24/7'}}
        db.execute('INSERT INTO osm VALUES (?,?,?,?,?,?,?,?,?)',
                   (123, 'Compact Cafe', common.norm('Compact Cafe'), 'node', LAT, LON, 'yes', 'yes',
                    _zlib(json.dumps(raw).encode())))
    db.commit()
    db.close()


def make_travel_db(path):
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE page (id INTEGER PRIMARY KEY, title TEXT, revision INTEGER, timestamp TEXT,'
               ' redirect TEXT, wikitext_zlib BLOB)')
    db.execute('CREATE TABLE listing (page INTEGER, ordinal INTEGER, lat REAL, lon REAL, name TEXT)')
    wiki = b'= New York =\nSome text.'
    db.execute('INSERT INTO page VALUES (?,?,?,?,?,?)',
               (1, 'New York', 12345, '2026-01-01T00:00:00Z', None, _zlib(wiki)))
    db.execute('INSERT INTO listing VALUES (?,?,?,?,?)', (1, 0, LAT, LON, 'Test Cafe'))
    db.commit()
    db.close()


class ReadonlySqliteHelperTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_opens_and_reads_every_special_filename(self):
        for name in SPECIAL_NAMES:
            with self.subTest(name=name):
                path = self.dir / name
                make_places_db(path)
                db = common.readonly_sqlite(path)
                try:
                    self.assertEqual(db.execute('SELECT count(*) FROM place').fetchone()[0], 1)
                finally:
                    db.close()

    def test_accepts_str_and_path(self):
        path = self.dir / 'with space.sqlite'
        make_places_db(path)
        for given in (str(path), path):
            with self.subTest(given=type(given).__name__):
                db = common.readonly_sqlite(given)
                try:
                    self.assertEqual(db.execute('SELECT name FROM place').fetchone()[0], 'Test Cafe')
                finally:
                    db.close()

    def test_connection_is_readonly(self):
        path = self.dir / 'with space.sqlite'
        make_places_db(path)
        db = common.readonly_sqlite(path)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                db.execute('CREATE TABLE t (x)')
            with self.assertRaises(sqlite3.OperationalError):
                db.execute('UPDATE place SET name=?', ('x',))
        finally:
            db.close()

    def test_missing_file_raises_operational_error_and_creates_nothing(self):
        for name in SPECIAL_NAMES:
            with self.subTest(name=name):
                path = self.dir / name
                self.assertFalse(path.exists())
                with self.assertRaises(sqlite3.OperationalError):
                    common.readonly_sqlite(path)
                self.assertFalse(path.exists())
                self.assertEqual(os.listdir(self.dir), [],
                                 'no database or journal side effects may be created')


class SearchModuleTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_search_and_source_with_special_filenames(self):
        for name in SPECIAL_NAMES:
            with self.subTest(name=name):
                path = self.dir / name
                make_places_db(path)
                rows = search.search([str(path)], LAT, LON, radius_km=10, category='cafe')
                self.assertEqual(len(rows), 1)
                row = rows[0]
                self.assertEqual(row['name'], 'Test Cafe')
                self.assertEqual(row['shard'], str(path))
                self.assertIsNone(row['live_status'])
                src = search.source(str(path), row['id'])
                self.assertEqual(src['record']['name'], 'Test Cafe')
                self.assertEqual(src['row_ordinal'], 7)
                self.assertEqual(src['provenance']['release'], '2026-09-23.1')
                self.assertEqual(src['entity_sibling_count'], 1)
                self.assertEqual(src['id_conflict_count'], 1)
                self.assertEqual(src['id_conflicts'][0]['row_ordinal'], 1)


class CompactSearchModuleTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_search_source_group_sources_with_special_filenames(self):
        for name in SPECIAL_NAMES:
            with self.subTest(name=name):
                path = self.dir / name
                make_compact_db(path)
                rows = compact_search.search([str(path)], LAT, LON, radius_km=10, category='cafe')
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['name'], 'Compact Cafe')
                self.assertEqual(rows[0]['shard'], str(path))
                self.assertEqual(rows[0]['block_id'], 1)
                src = compact_search.source(str(path), 1, 0, 'c1')
                self.assertEqual(src['record']['id'], 'c1')
                self.assertEqual(src['provenance']['release'], '2026-09-23.1')
                variants = list(compact_search.group_sources([str(path)], 'Compact Cafe', LAT, LON, 'cafe'))
                self.assertEqual(len(variants), 1)
                self.assertEqual(variants[0]['source_ordinal'], 0)


class EnrichModuleTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_cities_and_osm_candidates_with_special_filenames(self):
        for name in SPECIAL_NAMES:
            with self.subTest(name=name):
                city_db, osm_db = self.dir / (name + '.city'), self.dir / (name + '.osm')
                make_city_db(city_db)
                make_osm_db(osm_db)
                cities = enrich.cities(str(city_db), 'New York')
                self.assertEqual(len(cities), 1)
                self.assertEqual(cities[0]['name'], 'New York')
                cands = enrich.osm_candidates(str(osm_db), 'Compact Cafe', LAT, LON)
                self.assertEqual(len(cands), 1)
                self.assertEqual(cands[0]['match_status'],
                                 'candidate_exact_normalized_name_within_50m_unconfirmed')
                self.assertEqual(cands[0]['name'], 'Compact Cafe')

    def test_osm_search_noncompact_and_compact_with_special_filenames(self):
        for name in SPECIAL_NAMES:
            with self.subTest(name=name):
                osm_db = self.dir / name
                make_osm_db(osm_db)
                rows = enrich.osm_search(str(osm_db), LAT, LON, radius_km=10, diet='vegan')
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['name'], 'Compact Cafe')
                self.assertEqual(rows[0]['live_status'], None)
                compact_db = self.dir / (name + '.compact')
                make_osm_db(compact_db, compact=True)
                rows = enrich.osm_search(str(compact_db), LAT, LON, radius_km=10, diet='vegan')
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['name'], 'Compact Cafe')
                self.assertEqual(rows[0]['snapshot'], 'snapshot-sha')


class CatalogModuleTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _build(self, name):
        places = self.dir / (name + '.places')
        city_db = self.dir / (name + '.city')
        osm_db = self.dir / (name + '.osm')
        travel_db = self.dir / (name + '.travel')
        make_compact_db(places)
        make_city_db(city_db)
        make_osm_db(osm_db)
        make_travel_db(travel_db)
        return catalog.Catalog([str(places)], str(city_db), str(osm_db), str(travel_db))

    def test_catalog_facade_with_special_filenames(self):
        for name in SPECIAL_NAMES:
            with self.subTest(name=name):
                cat = self._build(name)
                self.assertEqual(cat.city_candidates('New York')[0]['name'], 'New York')
                nearby = cat.nearby(LAT, LON, radius_km=10, category='cafe')
                self.assertEqual(nearby['source_family'], 'Overture')
                self.assertEqual(len(nearby['snapshot_results']), 1)
                self.assertEqual(nearby['snapshot_results'][0]['name'], 'Compact Cafe')
                self.assertEqual(len(nearby['snapshot_results'][0]['osm_candidate_sources']), 1)
                self.assertIsNone(nearby['live_status'])
                variants = list(cat.source_variants(nearby['snapshot_results'][0]))
                self.assertEqual(len(variants), 1)
                src = cat.source(nearby['snapshot_results'][0]['shard'], 1, 0, 'c1')
                self.assertEqual(src['record']['id'], 'c1')
                diet = cat.nearby(LAT, LON, radius_km=10, diet='vegan')
                self.assertEqual(diet['source_family'], 'OpenStreetMap')
                self.assertEqual(diet['snapshot_results'][0]['name'], 'Compact Cafe')
                pages = cat.travel('New York')
                self.assertEqual(len(pages), 1)
                self.assertEqual(pages[0]['license'], 'CC-BY-SA-4.0')
                self.assertIn('oldid=12345', pages[0]['source_url'])
                source = cat.travel_source(1)
                self.assertEqual(source['wikitext'], '= New York =\nSome text.')
                self.assertEqual(len(source['listings']), 1)
                self.assertIsNone(cat.travel_source(999))
                near = cat.travel_nearby(LAT, LON, radius_km=10)
                self.assertEqual(len(near), 1)
                self.assertEqual(near[0]['title'], 'New York')
                self.assertEqual(near[0]['identity_kind'],
                                 'article listing occurrence, not a proven unique place')
                self.assertEqual(cat.enrichment_candidates('Compact Cafe', LAT, LON)[0]['name'],
                                 'Compact Cafe')


if __name__ == '__main__':
    unittest.main(verbosity=2)
