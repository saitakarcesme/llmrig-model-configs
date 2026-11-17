"""Regression tests for Catalog.nearby name/city keyword filters.

Standard-library unittest only. All fixtures (Overture shard, OSM db, city db)
are built in a temporary directory so the tests are self-contained.
"""
import hashlib
import json
import math
import os
import sqlite3
import tempfile
import unittest
import zlib

from catalog import Catalog
from common import norm

LAT, LON = 48.85, 2.35

PLACE_A = {'id': 'a1', 'name': 'Café Lumière', 'lat': 48.85, 'lon': 2.35, 'category': 'cafe', 'city': 'Paris'}
PLACE_B = {'id': 'b1', 'name': 'Brasserie du Port', 'lat': 48.852, 'lon': 2.352, 'category': 'restaurant', 'city': 'Lyon'}

OSM_ROWS = [
 {'id': 1, 'name': 'Café Lumière', 'lat': 48.8501, 'lon': 2.3501, 'type': 'cafe', 'vegan': 'yes', 'vegetarian': 'yes',
  'tags': {'name': 'Café Lumière', 'cuisine': 'international'}},
 {'id': 2, 'name': 'Green Bowl', 'lat': 48.851, 'lon': 2.351, 'type': 'restaurant', 'vegan': 'yes', 'vegetarian': 'no',
  'tags': {'name': 'Green Bowl'}},
 {'id': 3, 'name': 'Cheese Corner', 'lat': 48.852, 'lon': 2.352, 'type': 'cafe', 'vegan': 'no', 'vegetarian': 'yes',
  'tags': {'name': 'Cheese Corner'}},
]


def _grid(lat, lon):
    # Same cell math as compact_search.search / group_sources.
    return math.floor((lat + 90) * 10), math.floor((lon + 180) * 10)


def _make_shard(path, places):
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE block (id INTEGER PRIMARY KEY, payload BLOB, sha256 TEXT)')
    db.execute('CREATE TABLE grid (block INTEGER, gy INTEGER, gx INTEGER)')
    db.execute('CREATE TABLE category (category TEXT, block INTEGER)')
    db.execute('CREATE TABLE city (city TEXT, block INTEGER)')
    db.execute('CREATE TABLE metadata (key TEXT, value TEXT)')
    records = []
    for ordinal, p in enumerate(places):
        records.append([ordinal, p['lat'], p['lon'], norm(p['name']), {
            'id': p['id'],
            'names': {'primary': p['name']},
            'taxonomy': {'primary': p['category'], 'hierarchy': [p['category']], 'alternates': []},
            'basic_category': p['category'],
            'addresses': [{'locality': p['city'], 'country': 'France'}],
            'confidence': 0.9,
            'operating_status': 'active',
        }])
    raw = json.dumps(records).encode('utf-8')
    payload = zlib.compress(raw)
    db.execute('INSERT INTO block VALUES (1, ?, ?)', (payload, hashlib.sha256(raw).hexdigest()))
    for p in places:
        gy, gx = _grid(p['lat'], p['lon'])
        db.execute('INSERT INTO grid VALUES (1, ?, ?)', (gy, gx))
        db.execute('INSERT INTO category VALUES (?, 1)', (p['category'],))
        db.execute('INSERT INTO city VALUES (?, 1)', (p['city'],))
    db.commit()
    db.close()


def _make_osm(path, rows):
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE osm (id INTEGER PRIMARY KEY, name_key TEXT, lat REAL, lon REAL, '
               'type TEXT, vegan TEXT, vegetarian TEXT, raw BLOB)')
    for r in rows:
        db.execute('INSERT INTO osm VALUES (?,?,?,?,?,?,?,?)',
                   (r['id'], norm(r['name']), r['lat'], r['lon'], r['type'], r['vegan'], r['vegetarian'],
                    zlib.compress(json.dumps(r['tags'], ensure_ascii=False).encode('utf-8'))))
    db.commit()
    db.close()


def _make_city_db(path):
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE city (id INTEGER PRIMARY KEY, name TEXT, population INTEGER)')
    db.execute('CREATE TABLE alias (name_key TEXT, city_id INTEGER)')
    db.execute("INSERT INTO city VALUES (1, 'Paris', 2160000)")
    db.execute("INSERT INTO city VALUES (2, 'Lyon', 520000)")
    db.execute("INSERT INTO alias VALUES ('paris', 1)")
    db.execute("INSERT INTO alias VALUES ('lyon', 2)")
    db.commit()
    db.close()


class NearbyFilterTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.shard = os.path.join(tmp.name, 'shard0.db')
        self.osm_db = os.path.join(tmp.name, 'osm.db')
        self.city_db = os.path.join(tmp.name, 'city.db')
        self.travel_db = os.path.join(tmp.name, 'travel.db')  # never opened by nearby
        _make_shard(self.shard, [PLACE_A, PLACE_B])
        _make_osm(self.osm_db, OSM_ROWS)
        _make_city_db(self.city_db)
        self.cat = Catalog([self.shard], self.city_db, self.osm_db, self.travel_db)

    def _names(self, result):
        return [row['name'] for row in result['snapshot_results']]

    def test_default_contract_unchanged(self):
        result = self.cat.nearby(LAT, LON)
        self.assertEqual(set(result), {'source_family', 'snapshot_results', 'live_status', 'enrichment_semantics'})
        self.assertEqual(result['source_family'], 'Overture')
        self.assertIsNone(result['live_status'])
        self.assertEqual(self._names(result), ['Café Lumière', 'Brasserie du Port'])
        for row in result['snapshot_results']:
            self.assertIsNone(row['live_status'])
            self.assertIn('osm_candidate_sources', row)
            self.assertEqual(row['shard'], self.shard)
            self.assertEqual(row['city'], PLACE_A['city'] if row['name'] == PLACE_A['name'] else PLACE_B['city'])

    def test_name_filter_uses_exact_normalized_name(self):
        # Case/whitespace-insensitive exact-name match, as normalized in compact_search.
        self.assertEqual(self._names(self.cat.nearby(LAT, LON, name='CAFÉ  LUMIÈRE ')), ['Café Lumière'])
        # A name that exists only in the OSM source must not leak into Overture results.
        self.assertEqual(self._names(self.cat.nearby(LAT, LON, name='Green Bowl')), [])

    def test_city_filter_uses_exact_city(self):
        self.assertEqual(self._names(self.cat.nearby(LAT, LON, city='Paris')), ['Café Lumière'])
        self.assertEqual(self._names(self.cat.nearby(LAT, LON, city='Lyon')), ['Brasserie du Port'])
        self.assertEqual(self._names(self.cat.nearby(LAT, LON, city='Marseille')), [])

    def test_name_and_city_filters_combine(self):
        self.assertEqual(self._names(self.cat.nearby(LAT, LON, name='Café Lumière', city='Paris')), ['Café Lumière'])
        self.assertEqual(self._names(self.cat.nearby(LAT, LON, name='Café Lumière', city='Lyon')), [])

    def test_category_filter_still_works(self):
        self.assertEqual(self._names(self.cat.nearby(LAT, LON, category='cafe')), ['Café Lumière'])
        self.assertEqual(self._names(self.cat.nearby(LAT, LON, category='restaurant')), ['Brasserie du Port'])
        self.assertEqual(self._names(self.cat.nearby(LAT, LON, category='bar')), [])

    def test_limit_still_applies(self):
        self.assertEqual(len(self.cat.nearby(LAT, LON, limit=1)['snapshot_results']), 1)

    def test_positional_arguments_unchanged(self):
        # All six pre-existing positional arguments keep their order and meaning.
        self.assertEqual(self._names(self.cat.nearby(LAT, LON, 10, 'cafe', None, 20)), ['Café Lumière'])
        # New filters are appended after limit and also work positionally.
        self.assertEqual(self._names(self.cat.nearby(LAT, LON, 10, None, None, 20, 'Café Lumière', 'Paris')),
                         ['Café Lumière'])

    def test_diet_only_still_supported(self):
        result = self.cat.nearby(LAT, LON, diet='vegan')
        self.assertEqual(set(result), {'source_family', 'snapshot_results', 'live_status'})
        self.assertEqual(result['source_family'], 'OpenStreetMap')
        self.assertIsNone(result['live_status'])
        self.assertEqual([r['name_key'] for r in result['snapshot_results']], ['café lumière', 'green bowl'])
        for row in result['snapshot_results']:
            self.assertIsNone(row['live_status'])
            self.assertGreaterEqual(row['distance_km'], 0.0)

    def test_diet_with_name_raises(self):
        for name in ('Café Lumière', ''):  # explicit empty string counts as a provided filter
            with self.assertRaises(ValueError):
                self.cat.nearby(LAT, LON, diet='vegan', name=name)

    def test_diet_with_city_raises(self):
        for city in ('Paris', ''):
            with self.assertRaises(ValueError):
                self.cat.nearby(LAT, LON, diet='vegan', city=city)

    def test_diet_with_category_raises(self):
        with self.assertRaises(ValueError):
            self.cat.nearby(LAT, LON, diet='vegan', category='cafe')

    def test_enrichment_candidates_intact(self):
        result = self.cat.nearby(LAT, LON)
        by_name = {row['name']: row for row in result['snapshot_results']}
        candidates = by_name['Café Lumière']['osm_candidate_sources']
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]['match_status'], 'candidate_exact_normalized_name_within_50m_unconfirmed')
        self.assertIn('Café Lumière', candidates[0]['raw'])
        self.assertEqual(by_name['Brasserie du Port']['osm_candidate_sources'], [])

    def test_source_variants_attribution_intact(self):
        row = self.cat.nearby(LAT, LON, name='Café Lumière')['snapshot_results'][0]
        variants = list(self.cat.source_variants(row))
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0]['id'], 'a1')
        self.assertEqual(variants[0]['shard'], self.shard)
        self.assertIn('identity_status', variants[0])

    def test_city_candidates_intact(self):
        self.assertEqual(self.cat.city_candidates('Paris'), [{'id': 1, 'name': 'Paris', 'population': 2160000}])


if __name__ == '__main__':
    unittest.main()
