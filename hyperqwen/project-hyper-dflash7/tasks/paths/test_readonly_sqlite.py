"""Regression tests for read-only SQLite access with hostile filenames.

Covers the fix that routes every read-only connection through
``common.readonly_sqlite`` (percent-encoded ``file:...?mode=ro`` URI) so that
database filenames containing spaces, Unicode, ``#``, ``?``, ``&`` or a literal
``%`` open correctly, existing files stay read-only, and missing files raise
``sqlite3.OperationalError`` without creating anything.

Standard library only.
"""
import hashlib
import json
import math
import os
import shutil
import sqlite3
import tempfile
import unittest
import uuid
import zlib

import common
import search
import compact_search
import enrich
import catalog
from common import norm

# Filenames that used to break the raw ``file:<path>?mode=ro`` URI.
SPECIAL_NAMES = [
    "plain.sqlite",
    "with space.sqlite",
    "unicode_\u00e9_\u00f1_\u4e2d.sqlite",
    "hash#tag.sqlite",
    "question?mark.sqlite",
    "amp&ersand.sqlite",
    "percent%20literal.sqlite",
    "combo #?&% space \u00e9.sqlite",
]

# One "worst case" name exercising every hostile character at once, used for the
# end-to-end module tests.
HARD_NAME = "hard #?&% space \u00e9\u4e2d.sqlite"


def _mkpath(tmp, name):
    return os.path.join(tmp, name)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


class TestReadonlySqliteHelper(unittest.TestCase):
    """Unit tests for the shared ``common.readonly_sqlite`` helper."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ro_sqlite_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _make(self, name):
        p = _mkpath(self.tmp, name)
        db = sqlite3.connect(p)
        db.execute("CREATE TABLE t(x TEXT)")
        db.execute("INSERT INTO t VALUES('hello')")
        db.commit()
        db.close()
        return p

    def test_reads_every_special_character_filename(self):
        for name in SPECIAL_NAMES:
            with self.subTest(name=name):
                p = self._make(name)
                db = common.readonly_sqlite(p)
                try:
                    self.assertEqual(db.execute("SELECT x FROM t").fetchone(), ("hello",))
                finally:
                    db.close()

    def test_existing_file_stays_readonly(self):
        for name in SPECIAL_NAMES:
            with self.subTest(name=name):
                p = self._make(name)
                before = os.path.getmtime(p)
                db = common.readonly_sqlite(p)
                try:
                    with self.assertRaises(sqlite3.OperationalError):
                        db.execute("INSERT INTO t VALUES('x')")
                    with self.assertRaises(sqlite3.OperationalError):
                        db.execute("CREATE TABLE y(z)")
                finally:
                    db.close()
                self.assertEqual(os.path.getmtime(p), before, "file was modified")

    def test_missing_file_raises_without_creating(self):
        for name in SPECIAL_NAMES:
            with self.subTest(name=name):
                p = _mkpath(self.tmp, name)
                self.assertFalse(os.path.exists(p))
                with self.assertRaises(sqlite3.OperationalError):
                    common.readonly_sqlite(p)
                self.assertFalse(os.path.exists(p), "missing file was created")

    def test_accepts_pathlib_path_and_str(self):
        import pathlib
        p = self._make("mixed.sqlite")
        via_str = common.readonly_sqlite(p)
        via_path = common.readonly_sqlite(pathlib.Path(p))
        self.assertEqual(via_str.execute("SELECT x FROM t").fetchone(), ("hello",))
        self.assertEqual(via_path.execute("SELECT x FROM t").fetchone(), ("hello",))
        via_str.close()
        via_path.close()

    def test_relative_path_is_resolved(self):
        p = self._make("rel.sqlite")
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.tmp)
        try:
            db = common.readonly_sqlite("rel.sqlite")
            try:
                self.assertEqual(db.execute("SELECT x FROM t").fetchone(), ("hello",))
            finally:
                db.close()
        finally:
            os.chdir(cwd)


# ---------------------------------------------------------------------------
# Database builders (minimal but schema-faithful) for the end-to-end tests.
# ---------------------------------------------------------------------------

def build_search_db(path):
    """Overture-style shard for ``search.py``. Returns the place identity."""
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE place(id BLOB, name TEXT, lat REAL, lon REAL, category TEXT,"
        " city TEXT, country TEXT, confidence REAL, status TEXT, entity_key BLOB,"
        " gy INTEGER, gx INTEGER, name_key TEXT, detail BLOB, ordinal INTEGER)")
    db.execute("CREATE TABLE category(place_id BLOB, category TEXT)")
    db.execute("CREATE TABLE progress(key TEXT, value TEXT)")
    db.execute("CREATE TABLE conflict(id BLOB, ordinal INTEGER, detail BLOB)")
    place_id = uuid.uuid4().bytes
    entity_key = uuid.uuid4().bytes
    detail = zlib.compress(json.dumps(
        {"id": str(uuid.UUID(bytes=place_id)), "name": "Test Place"}).encode())
    gy = math.floor((40.0 + 90) * 100)
    gx = math.floor((-74.0 + 180) * 100)
    db.execute(
        "INSERT INTO place(id,name,lat,lon,category,city,country,confidence,status,"
        "entity_key,gy,gx,name_key,detail,ordinal) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (place_id, "Test Place", 40.0, -74.0, "cafe", "New York", "US", 0.9,
         "open", entity_key, gy, gx, norm("Test Place"), detail, 0))
    db.execute("INSERT INTO category VALUES(?,?)", (place_id, "cafe"))
    for k, v in [("release", "2026-09-23.1"), ("source", "places.parquet"),
                 ("source_sha256", "abc123"), ("schema_version", 2)]:
        db.execute("INSERT INTO progress VALUES(?,?)", (k, json.dumps(v)))
    db.execute("INSERT INTO conflict VALUES(?,?,?)",
               (place_id, 0, zlib.compress(json.dumps({"note": "conflict"}).encode())))
    db.commit()
    db.close()
    return str(uuid.UUID(bytes=place_id))


def build_compact_db(path):
    """Schema-v2 block shard for ``compact_search.py``. Returns (block, id)."""
    record = {
        "id": "rec-1",
        "names": {"primary": "Test Cafe"},
        "taxonomy": {"primary": "cafe", "hierarchy": ["cafe"], "alternates": []},
        "basic_category": "cafe",
        "addresses": [{"locality": "New York", "country": "US"}],
        "confidence": 0.9,
        "operating_status": "open",
    }
    block = "block-1"
    payload_list = [[0, 40.0, -74.0, norm("Test Cafe"), record]]
    raw = json.dumps(payload_list).encode()
    payload = zlib.compress(raw)
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE grid(block TEXT, gy INTEGER, gx INTEGER)")
    db.execute("CREATE TABLE block(id TEXT, payload BLOB, sha256 TEXT)")
    db.execute("CREATE TABLE category(category TEXT, block TEXT)")
    db.execute("CREATE TABLE city(city TEXT, block TEXT)")
    db.execute("CREATE TABLE metadata(key TEXT, value TEXT)")
    gy = math.floor((40.0 + 90) * 10)
    gx = math.floor((-74.0 + 180) * 10)
    db.execute("INSERT INTO grid VALUES(?,?,?)", (block, gy, gx))
    db.execute("INSERT INTO block VALUES(?,?,?)", (block, payload, _sha(raw)))
    db.execute("INSERT INTO category VALUES(?,?)", ("cafe", block))
    db.execute("INSERT INTO city VALUES(?,?)", ("New York", block))
    db.execute("INSERT INTO metadata VALUES(?,?)", ("schema", json.dumps("2")))
    db.execute("INSERT INTO metadata VALUES(?,?)", ("source", json.dumps("places.parquet")))
    db.commit()
    db.close()
    return block, "rec-1"


def build_enrich_db(path):
    """OSM/city enrichment shard for ``enrich.py`` (non-compact)."""
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE city(id INTEGER, name TEXT, population INTEGER, country TEXT)")
    db.execute("CREATE TABLE alias(name_key TEXT, city_id INTEGER)")
    db.execute(
        "CREATE TABLE osm(id INTEGER, name_key TEXT, lat REAL, lon REAL, type TEXT,"
        " vegan TEXT, vegetarian TEXT, raw TEXT)")
    db.execute("INSERT INTO city VALUES(1,'New York',8000000,'US')")
    db.execute("INSERT INTO alias VALUES(?,1)", (norm("New York"),))
    db.execute(
        "INSERT INTO osm VALUES(1,?,40.0,-74.0,'cafe','yes','no',?)",
        (norm("Test Cafe"), json.dumps({"name": "Test Cafe", "diet:vegan": "yes"})))
    db.commit()
    db.close()


def build_travel_db(path):
    """Wikivoyage-style travel shard for ``catalog.py``."""
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE page(id INTEGER, title TEXT, revision INTEGER, timestamp TEXT,"
        " redirect TEXT, wikitext_zlib BLOB)")
    db.execute("CREATE TABLE listing(page INTEGER, ordinal INTEGER, lat REAL, lon REAL, name TEXT)")
    wikitext = "New York is a city."
    db.execute(
        "INSERT INTO page VALUES(1,'New York',42,'2026-01-01',NULL,?)",
        (zlib.compress(wikitext.encode()),))
    db.execute("INSERT INTO listing VALUES(1,0,40.0,-74.0,'Test Listing')")
    db.commit()
    db.close()


class TestSearchModule(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="search_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = _mkpath(self.tmp, HARD_NAME)
        self.identity = build_search_db(self.path)

    def test_search_finds_place(self):
        rows = search.search([self.path], 40.0, -74.0, 10.0)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["name"], "Test Place")
        self.assertEqual(r["category"], "cafe")
        self.assertEqual(r["city"], "New York")
        self.assertEqual(r["id"], self.identity)
        self.assertEqual(r["shard"], str(self.path))
        self.assertIsNone(r["diet"])
        self.assertIsNone(r["live_status"])
        self.assertLess(r["distance_km"], 1.0)

    def test_search_category_filter(self):
        self.assertEqual(len(search.search([self.path], 40.0, -74.0, 10.0, category="cafe")), 1)
        self.assertEqual(len(search.search([self.path], 40.0, -74.0, 10.0, category="bakery")), 0)

    def test_search_name_filter(self):
        self.assertEqual(len(search.search([self.path], 40.0, -74.0, 10.0, name="test place")), 1)
        self.assertEqual(len(search.search([self.path], 40.0, -74.0, 10.0, name="nope")), 0)

    def test_source_returns_provenance(self):
        s = search.source(self.path, self.identity)
        self.assertIsNotNone(s)
        self.assertEqual(s["record"]["name"], "Test Place")
        self.assertEqual(s["row_ordinal"], 0)
        self.assertEqual(s["provenance"]["release"], "2026-09-23.1")
        self.assertEqual(s["provenance"]["schema_version"], 2)
        self.assertEqual(s["entity_sibling_count"], 1)
        self.assertEqual(s["id_conflict_count"], 1)
        self.assertEqual(s["id_conflicts"][0]["record"]["note"], "conflict")

    def test_source_unknown_identity(self):
        self.assertIsNone(search.source(self.path, str(uuid.uuid4())))

    def test_missing_shard_raises(self):
        with self.assertRaises(sqlite3.OperationalError):
            search.search([_mkpath(self.tmp, "missing #?&%.sqlite")], 40.0, -74.0, 10.0)


class TestCompactSearchModule(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="compact_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = _mkpath(self.tmp, HARD_NAME)
        self.block, self.rec_id = build_compact_db(self.path)

    def test_search_finds_record(self):
        rows = compact_search.search([self.path], 40.0, -74.0, 10.0)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["id"], "rec-1")
        self.assertEqual(r["name"], "Test Cafe")
        self.assertEqual(r["category"], "cafe")
        self.assertEqual(r["city"], "New York")
        self.assertEqual(r["block_id"], self.block)
        self.assertLess(r["distance_km"], 1.0)

    def test_search_category_filter(self):
        self.assertEqual(len(compact_search.search([self.path], 40.0, -74.0, 10.0, category="cafe")), 1)
        self.assertEqual(len(compact_search.search([self.path], 40.0, -74.0, 10.0, category="bakery")), 0)

    def test_source_returns_record(self):
        s = compact_search.source(self.path, self.block, 0, "rec-1")
        self.assertIsNotNone(s)
        self.assertEqual(s["record"]["id"], "rec-1")
        self.assertEqual(s["latitude"], 40.0)
        self.assertEqual(s["longitude"], -74.0)
        self.assertEqual(s["row_ordinal"], 0)
        self.assertEqual(s["provenance"]["schema"], "2")

    def test_source_wrong_identity(self):
        self.assertIsNone(compact_search.source(self.path, self.block, 0, "nope"))

    def test_group_sources(self):
        groups = list(compact_search.group_sources([self.path], "Test Cafe", 40.0, -74.0, "cafe"))
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["id"], "rec-1")
        self.assertEqual(groups[0]["block_id"], self.block)

    def test_missing_shard_raises(self):
        with self.assertRaises(sqlite3.OperationalError):
            compact_search.search([_mkpath(self.tmp, "missing #?&%.sqlite")], 40.0, -74.0, 10.0)


class TestEnrichModule(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="enrich_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = _mkpath(self.tmp, HARD_NAME)
        build_enrich_db(self.path)

    def test_cities(self):
        rows = enrich.cities(self.path, "New York")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "New York")
        self.assertEqual(rows[0]["population"], 8000000)

    def test_osm_candidates(self):
        rows = enrich.osm_candidates(self.path, "Test Cafe", 40.0, -74.0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["match_status"],
                         "candidate_exact_normalized_name_within_50m_unconfirmed")
        self.assertEqual(json.loads(rows[0]["raw"])["name"], "Test Cafe")

    def test_osm_search(self):
        rows = enrich.osm_search(self.path, 40.0, -74.0, 10.0)
        self.assertEqual(len(rows), 1)
        self.assertLess(rows[0]["distance_km"], 1.0)
        self.assertIsNone(rows[0]["live_status"])

    def test_osm_search_diet_filter(self):
        self.assertEqual(len(enrich.osm_search(self.path, 40.0, -74.0, 10.0, diet="vegan")), 1)
        self.assertEqual(len(enrich.osm_search(self.path, 40.0, -74.0, 10.0, diet="vegetarian")), 0)

    def test_osm_search_rejects_bad_diet(self):
        with self.assertRaises(ValueError):
            enrich.osm_search(self.path, 40.0, -74.0, 10.0, diet="paleo")

    def test_missing_db_raises(self):
        with self.assertRaises(sqlite3.OperationalError):
            enrich.cities(_mkpath(self.tmp, "missing #?&%.sqlite"), "New York")


class TestCatalogModule(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="catalog_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.places = _mkpath(self.tmp, "places #?&%.sqlite")
        self.city_db = _mkpath(self.tmp, "city #?&%.sqlite")
        self.osm_db = _mkpath(self.tmp, "osm #?&%.sqlite")
        self.travel_db = _mkpath(self.tmp, "travel #?&%.sqlite")
        build_compact_db(self.places)   # nearby() Overture branch uses compact_search.search
        build_enrich_db(self.city_db)
        build_enrich_db(self.osm_db)
        build_travel_db(self.travel_db)
        self.cat = catalog.Catalog([self.places], self.city_db, self.osm_db, self.travel_db)

    def test_travel(self):
        rows = self.cat.travel("New York")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "New York")
        self.assertEqual(rows[0]["license"], "CC-BY-SA-4.0")
        self.assertTrue(rows[0]["source_url"].endswith("oldid=42"))

    def test_travel_source(self):
        s = self.cat.travel_source(1)
        self.assertIsNotNone(s)
        self.assertEqual(s["wikitext"], "New York is a city.")
        self.assertEqual(len(s["listings"]), 1)
        self.assertEqual(s["license"], "CC-BY-SA-4.0")
        self.assertTrue(s["source_url"].endswith("oldid=42"))

    def test_travel_source_missing(self):
        self.assertIsNone(self.cat.travel_source(999))

    def test_travel_nearby(self):
        rows = self.cat.travel_nearby(40.0, -74.0, 10.0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Test Listing")
        self.assertLess(rows[0]["distance_km"], 1.0)
        self.assertIsNone(rows[0]["live_status"])

    def test_nearby_overture_family(self):
        result = self.cat.nearby(40.0, -74.0, 10.0)
        self.assertEqual(result["source_family"], "Overture")
        self.assertIsNone(result["live_status"])
        self.assertEqual(len(result["snapshot_results"]), 1)
        self.assertEqual(result["snapshot_results"][0]["name"], "Test Cafe")
        # OSM candidate enrichment is attached to each Overture row
        self.assertIn("osm_candidate_sources", result["snapshot_results"][0])

    def test_nearby_osm_family(self):
        result = self.cat.nearby(40.0, -74.0, 10.0, diet="vegan")
        self.assertEqual(result["source_family"], "OpenStreetMap")
        self.assertIsNone(result["live_status"])
        self.assertEqual(len(result["snapshot_results"]), 1)

    def test_nearby_rejects_category_plus_diet(self):
        with self.assertRaises(ValueError):
            self.cat.nearby(40.0, -74.0, 10.0, category="cafe", diet="vegan")

    def test_city_candidates(self):
        rows = self.cat.city_candidates("New York")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "New York")

    def test_missing_travel_db_raises(self):
        cat = catalog.Catalog([self.places], self.city_db, self.osm_db,
                              _mkpath(self.tmp, "missing #?&%.sqlite"))
        with self.assertRaises(sqlite3.OperationalError):
            cat.travel("New York")


if __name__ == "__main__":
    unittest.main(verbosity=2)
