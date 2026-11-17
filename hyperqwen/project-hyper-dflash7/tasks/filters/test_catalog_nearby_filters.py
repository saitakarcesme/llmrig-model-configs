"""Standard-library regression tests for Catalog.nearby name/city keyword filters.

Covers:
- preserved positional signature and default output contracts
- name/city filters forwarded to compact_search (normalized exact name, exact city)
- diet branch: diet-only still works; any non-None name/city/category (incl. '') raises ValueError
- source-family attribution, enrichment candidates and unknown live status intact
"""
import hashlib,inspect,json,math,os,sqlite3,sys,tempfile,unittest,zlib

HERE=os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:sys.path.insert(0,HERE)
import catalog

def _places():
 return [
  (0,40.0,-74.0,'alpha cafe',{
   'id':'id-a','names':{'primary':'Alpha Cafe'},
   'taxonomy':{'primary':'cafe','hierarchy':['cafe'],'alternates':[]},
   'basic_category':'cafe','addresses':[{'locality':'Springfield','country':'USA'}],
   'confidence':0.9,'operating_status':'active'}),
  (1,40.001,-74.001,'beta diner',{
   'id':'id-b','names':{'primary':'Beta Diner'},
   'taxonomy':{'primary':'restaurant','hierarchy':['restaurant'],'alternates':[]},
   'basic_category':'restaurant','addresses':[{'locality':'Springfield','country':'USA'}],
   'confidence':0.8,'operating_status':'active'}),
  (2,40.002,-74.002,'gamma cafe',{
   'id':'id-c','names':{'primary':'Gamma Cafe'},
   'taxonomy':{'primary':'cafe','hierarchy':['cafe'],'alternates':[]},
   'basic_category':'cafe','addresses':[{'locality':'Rivertown','country':'USA'}],
   'confidence':0.7,'operating_status':'active'}),
 ]

def make_places_shard(path):
 """Schema-v2 Overture shard: zlib+sha256 block, grid, block-level category/city, metadata."""
 rows=_places()
 raw=json.dumps(rows).encode('utf-8')
 payload=zlib.compress(raw)
 sha=hashlib.sha256(raw).hexdigest()
 db=sqlite3.connect(path)
 db.execute('CREATE TABLE block(id INTEGER PRIMARY KEY,payload BLOB,sha256 TEXT)')
 db.execute('CREATE TABLE grid(block INTEGER,gy INTEGER,gx INTEGER)')
 db.execute('CREATE TABLE category(category TEXT,block INTEGER)')
 db.execute('CREATE TABLE city(city TEXT,block INTEGER)')
 db.execute('CREATE TABLE metadata(key TEXT,value TEXT)')
 db.execute('INSERT INTO block VALUES (1,?,?)',(payload,sha))
 for _,lat,lon,_,_ in rows:
  db.execute('INSERT INTO grid VALUES (1,?,?)',(math.floor((lat+90)*10),math.floor((lon+180)*10)))
 for cat in ('cafe','restaurant'):
  db.execute('INSERT INTO category VALUES (?,1)',(cat,))
 for city in ('Springfield','Rivertown'):
  db.execute('INSERT INTO city VALUES (?,1)',(city,))
 db.execute("INSERT INTO metadata VALUES ('schema_version','2')")
 db.commit();db.close()

def make_osm_db(path):
 """Non-compact OSM staging db (no 'block' table, so is_compact() is False)."""
 rows=[
  (1,'alpha cafe','Alpha Cafe',40.0,-74.0,'cafe','yes','yes'),
  (2,'beta diner','Beta Diner',40.001,-74.001,'restaurant',None,'yes'),
  (3,'gamma cafe','Gamma Cafe',40.002,-74.002,'cafe','only',None),
 ]
 db=sqlite3.connect(path)
 db.execute('CREATE TABLE osm(id INTEGER PRIMARY KEY,name_key TEXT,name TEXT,lat REAL,lon REAL,type TEXT,vegan TEXT,vegetarian TEXT,raw BLOB)')
 for id_,nk,name,lat,lon,typ,veg,vegn in rows:
  raw=zlib.compress(json.dumps({'id':'osm-%d'%id_,'type':typ,'version':1,'tags':{'name':name,'diet:vegan':veg,'diet:vegetarian':vegn}}).encode('utf-8'))
  db.execute('INSERT INTO osm VALUES (?,?,?,?,?,?,?,?,?)',(id_,nk,name,lat,lon,typ,veg,vegn,raw))
 db.commit();db.close()

def make_city_db(path):
 db=sqlite3.connect(path)
 db.execute('CREATE TABLE city(id INTEGER PRIMARY KEY,name TEXT,population INTEGER)')
 db.execute('CREATE TABLE alias(name_key TEXT,city_id INTEGER)')
 db.execute("INSERT INTO city VALUES (1,'Springfield',100000)")
 db.execute("INSERT INTO alias VALUES ('springfield',1)")
 db.commit();db.close()

def make_travel_db(path):
 db=sqlite3.connect(path)
 db.execute('CREATE TABLE page(id INTEGER PRIMARY KEY,title TEXT,revision INTEGER,timestamp TEXT,redirect TEXT,wikitext_zlib BLOB)')
 db.execute('CREATE TABLE listing(page INTEGER,ordinal INTEGER,name TEXT,lat REAL,lon REAL)')
 db.execute("INSERT INTO page VALUES (1,'Springfield',42,'2024-01-01',NULL,?)",(zlib.compress(b'== Springfield ==\n'),))
 db.execute("INSERT INTO listing VALUES (1,0,'Alpha Cafe',40.0,-74.0)")
 db.commit();db.close()

class NearbyFilterTests(unittest.TestCase):
 def setUp(self):
  self._tmp=tempfile.TemporaryDirectory()
  d=self._tmp.name
  self.places=os.path.join(d,'places-0.sqlite')
  self.osm_db=os.path.join(d,'osm.sqlite')
  self.city_db=os.path.join(d,'cities.sqlite')
  self.travel_db=os.path.join(d,'travel.sqlite')
  make_places_shard(self.places);make_osm_db(self.osm_db);make_city_db(self.city_db);make_travel_db(self.travel_db)
  self.cat=catalog.Catalog([self.places],self.city_db,self.osm_db,self.travel_db)
  self.lat,self.lon=40.0,-74.0
 def tearDown(self):
  self._tmp.cleanup()

 def test_signature_keeps_existing_positional_contract(self):
  sig=inspect.signature(catalog.Catalog.nearby)
  self.assertEqual(list(sig.parameters)[:7],['self','lat','lon','radius_km','category','diet','limit'])
  self.assertEqual(list(sig.parameters)[7:],['name','city'])
  defaults={k:v.default for k,v in sig.parameters.items()}
  self.assertEqual(defaults['radius_km'],10)
  self.assertEqual(defaults['category'],None)
  self.assertEqual(defaults['diet'],None)
  self.assertEqual(defaults['limit'],20)
  self.assertEqual(defaults['name'],None)
  self.assertEqual(defaults['city'],None)

 def test_overture_baseline_contract_unchanged(self):
  res=self.cat.nearby(self.lat,self.lon)
  self.assertEqual(set(res),{'source_family','snapshot_results','live_status','enrichment_semantics'})
  self.assertEqual(res['source_family'],'Overture')
  self.assertIsNone(res['live_status'])
  self.assertEqual([r['name'] for r in res['snapshot_results']],['Alpha Cafe','Beta Diner','Gamma Cafe'])
  for r in res['snapshot_results']:
   self.assertIn('osm_candidate_sources',r)
   self.assertIsInstance(r['osm_candidate_sources'],list)
   self.assertIsNone(r['live_status'])
   self.assertIsNone(r['diet'])
   self.assertIsNone(r['hours'])
   self.assertEqual(r['shard'],self.places)
  alpha=next(r for r in res['snapshot_results'] if r['name']=='Alpha Cafe')
  self.assertEqual([c['name'] for c in alpha['osm_candidate_sources']],['Alpha Cafe'])
  self.assertEqual(alpha['osm_candidate_sources'][0]['match_status'],'candidate_exact_normalized_name_within_50m_unconfirmed')

 def test_name_filter_uses_compact_search_normalization(self):
  res=self.cat.nearby(self.lat,self.lon,name='ALPHA   cafe')
  self.assertEqual(res['source_family'],'Overture')
  self.assertEqual([r['name'] for r in res['snapshot_results']],['Alpha Cafe'])
  res=self.cat.nearby(self.lat,self.lon,name='No Such Place')
  self.assertEqual(res['snapshot_results'],[])
  self.assertIsNone(res['live_status'])

 def test_city_filter_is_exact(self):
  res=self.cat.nearby(self.lat,self.lon,city='Springfield')
  self.assertEqual(sorted(r['name'] for r in res['snapshot_results']),['Alpha Cafe','Beta Diner'])
  self.assertEqual(self.cat.nearby(self.lat,self.lon,city='springfield')['snapshot_results'],[])
  self.assertEqual(self.cat.nearby(self.lat,self.lon,city='Nowhere')['snapshot_results'],[])

 def test_combined_name_city_category_filters(self):
  res=self.cat.nearby(self.lat,self.lon,category='cafe',name='Gamma Cafe',city='Rivertown')
  self.assertEqual([r['name'] for r in res['snapshot_results']],['Gamma Cafe'])
  self.assertEqual(self.cat.nearby(self.lat,self.lon,category='cafe',name='Beta Diner')['snapshot_results'],[])
  self.assertEqual(self.cat.nearby(self.lat,self.lon,category='restaurant',city='Rivertown')['snapshot_results'],[])

 def test_empty_string_filters_in_overture_path_delegate_to_compact_search(self):
  res=self.cat.nearby(self.lat,self.lon,name='',city='')
  self.assertEqual([r['name'] for r in res['snapshot_results']],['Alpha Cafe','Beta Diner','Gamma Cafe'])

 def test_overture_row_contract_with_filters(self):
  res=self.cat.nearby(self.lat,self.lon,name='Beta Diner',city='Springfield')
  self.assertEqual(len(res['snapshot_results']),1)
  r=res['snapshot_results'][0]
  self.assertEqual(set(r),{'id','name','lat','lon','category','city','country','confidence','status','distance_km','shard','block_id','source_ordinal','hours','diet','live_status','osm_candidate_sources'})
  self.assertEqual(r['id'],'id-b')
  self.assertEqual(r['category'],'restaurant')
  self.assertEqual(r['city'],'Springfield')
  self.assertEqual(r['country'],'USA')
  self.assertIsNone(r['live_status'])
  self.assertEqual([c['name'] for c in r['osm_candidate_sources']],['Beta Diner'])

 def test_limit_and_radius_still_applied(self):
  self.assertEqual([r['name'] for r in self.cat.nearby(self.lat,self.lon,limit=1)['snapshot_results']],['Alpha Cafe'])
  self.assertEqual([r['name'] for r in self.cat.nearby(self.lat,self.lon,radius_km=0.01)['snapshot_results']],['Alpha Cafe'])
  with self.assertRaises(ValueError):self.cat.nearby(self.lat,self.lon,radius_km=0)

 def test_diet_only_calls_still_supported(self):
  res=self.cat.nearby(self.lat,self.lon,diet='vegan')
  self.assertEqual(set(res),{'source_family','snapshot_results','live_status'})
  self.assertEqual(res['source_family'],'OpenStreetMap')
  self.assertIsNone(res['live_status'])
  self.assertEqual([r['name'] for r in res['snapshot_results']],['Alpha Cafe','Gamma Cafe'])
  for r in res['snapshot_results']:self.assertIsNone(r['live_status'])
  res=self.cat.nearby(self.lat,self.lon,diet='vegetarian')
  self.assertEqual([r['name'] for r in res['snapshot_results']],['Alpha Cafe','Beta Diner'])
  with self.assertRaises(ValueError):self.cat.nearby(self.lat,self.lon,diet='paleo')

 def test_diet_with_any_non_none_filter_raises(self):
  for kwargs in (
   {'name':'Alpha Cafe'},
   {'city':'Springfield'},
   {'category':'cafe'},
   {'name':''},
   {'city':''},
   {'category':''},
   {'name':'Alpha Cafe','city':'Springfield'},
   {'name':'Alpha Cafe','category':'cafe','city':'Springfield'},
  ):
   with self.assertRaises(ValueError):self.cat.nearby(self.lat,self.lon,diet='vegan',**kwargs)

 def test_diet_category_error_message_preserved(self):
  with self.assertRaises(ValueError) as cm:
   self.cat.nearby(self.lat,self.lon,diet='vegan',category='cafe')
  self.assertEqual(str(cm.exception),'Cross-taxonomy category+diet join is unconfirmed')

 def test_empty_diet_is_not_selected(self):
  res=self.cat.nearby(self.lat,self.lon,diet='',name='Alpha Cafe')
  self.assertEqual(res['source_family'],'Overture')
  self.assertEqual([r['name'] for r in res['snapshot_results']],['Alpha Cafe'])

 def test_positional_calls_unchanged(self):
  self.assertEqual(self.cat.nearby(self.lat,self.lon,10,None,'vegan',20)['source_family'],'OpenStreetMap')
  with self.assertRaises(ValueError):self.cat.nearby(self.lat,self.lon,10,'cafe','vegan',20)
  self.assertEqual(sorted(r['name'] for r in self.cat.nearby(self.lat,self.lon,10,'cafe',None,20)['snapshot_results']),['Alpha Cafe','Gamma Cafe'])
  self.assertEqual([r['name'] for r in self.cat.nearby(self.lat,self.lon,10,None,None,20,'Alpha Cafe','Springfield')['snapshot_results']],['Alpha Cafe'])

 def test_city_candidates_and_travel_nearby_unchanged(self):
  self.assertEqual([r['name'] for r in self.cat.city_candidates('Springfield')],['Springfield'])
  rows=self.cat.travel_nearby(self.lat,self.lon,10)
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]['name'],'Alpha Cafe')
  self.assertEqual(rows[0]['license'],'CC-BY-SA-4.0')
  self.assertIsNone(rows[0]['live_status'])
  self.assertEqual(rows[0]['identity_kind'],'article listing occurrence, not a proven unique place')

if __name__=='__main__':
 unittest.main(verbosity=2)
