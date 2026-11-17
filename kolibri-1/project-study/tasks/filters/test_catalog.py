import unittest
from unittest import mock
import catalog

class TestCatalogNearby(unittest.TestCase):
    def setUp(self):
        # Dummy paths
        self.places = '/tmp/places.db'
        self.city_db = '/tmp/city.db'
        self.osm_db = '/tmp/osm.db'
        self.travel_db = '/tmp/travel.db'
        self.catalog = catalog.Catalog(self.places, self.city_db, self.osm_db, self.travel_db)

    @mock.patch('catalog.search')
    @mock.patch('catalog.osm_candidates')
    def test_nearby_without_diet_forwards_name_and_city(self, mock_osm_candidates, mock_search):
        # Mock search to return a list of rows
        mock_search.return_value = [{'name': 'Test', 'lat': 0, 'lon': 0, 'category': 'restaurant'}]
        mock_osm_candidates.return_value = []
        result = self.catalog.nearby(lat=0, lon=0, name='Test', city='London')
        # Verify search called with name and city
        mock_search.assert_called_once_with(self.places, 0, 0, radius_km=10, category=None, name='Test', diet=None, city='London', limit=20)
        # Verify osm_candidates called for each row
        mock_osm_candidates.assert_called_once_with(self.osm_db, 'Test', 0, 0)
        # Verify result structure
        self.assertEqual(result['source_family'], 'Overture')
        self.assertEqual(len(result['snapshot_results']), 1)

    @mock.patch('catalog.osm_search')
    def test_nearby_with_diet_only(self, mock_osm_search):
        mock_osm_search.return_value = []
        result = self.catalog.nearby(lat=0, lon=0, diet='vegan')
        mock_osm_search.assert_called_once_with(self.osm_db, 0, 0, radius_km=10, diet='vegan', limit=20)
        self.assertEqual(result['source_family'], 'OpenStreetMap')

    @mock.patch('catalog.osm_search')
    def test_nearby_with_diet_and_category_raises(self, mock_osm_search):
        with self.assertRaises(ValueError) as cm:
            self.catalog.nearby(lat=0, lon=0, diet='vegan', category='restaurant')
        self.assertEqual(str(cm.exception), 'Cross-source join with diet is unconfirmed')
        mock_osm_search.assert_not_called()

    @mock.patch('catalog.osm_search')
    def test_nearby_with_diet_and_name_raises(self, mock_osm_search):
        with self.assertRaises(ValueError) as cm:
            self.catalog.nearby(lat=0, lon=0, diet='vegan', name='Test')
        self.assertEqual(str(cm.exception), 'Cross-source join with diet is unconfirmed')
        mock_osm_search.assert_not_called()

    @mock.patch('catalog.osm_search')
    def test_nearby_with_diet_and_city_raises(self, mock_osm_search):
        with self.assertRaises(ValueError) as cm:
            self.catalog.nearby(lat=0, lon=0, diet='vegan', city='London')
        self.assertEqual(str(cm.exception), 'Cross-source join with diet is unconfirmed')
        mock_osm_search.assert_not_called()

    @mock.patch('catalog.search')
    @mock.patch('catalog.osm_candidates')
    def test_nearby_without_diet_default(self, mock_osm_candidates, mock_search):
        mock_search.return_value = []
        mock_osm_candidates.return_value = []
        result = self.catalog.nearby(lat=0, lon=0)
        mock_search.assert_called_once_with(self.places, 0, 0, radius_km=10, category=None, name=None, diet=None, city=None, limit=20)
        self.assertEqual(result['source_family'], 'Overture')

if __name__ == '__main__':
    unittest.main()