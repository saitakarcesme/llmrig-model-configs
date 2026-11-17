"""Frozen acceptance cases for independently scoped PocketLore changes."""
import sys,pathlib,unittest,tempfile,sqlite3,json,zlib,hashlib,random,base64,concurrent.futures
sys.path.insert(0,sys.argv.pop(1))
TASK=sys.argv.pop(1)
import common,compact_search,search,enrich,catalog

class Paths(unittest.TestCase):
 def test_public_helper_and_read_only(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/'München # ? & %25.sqlite';db=sqlite3.connect(p);db.execute('CREATE TABLE sentinel(x)');db.execute('INSERT INTO sentinel VALUES(17)');db.commit();db.close()
   for connect in [common.readonly_sqlite,compact_search.connect,enrich.connect]:
    with self.subTest(connect=connect.__module__):
     db=connect(p);self.assertEqual(db.execute('SELECT x FROM sentinel').fetchone()[0],17)
     with self.assertRaises(sqlite3.OperationalError):db.execute('INSERT INTO sentinel VALUES(18)')
     db.close()
 def test_missing_does_not_create(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/'missing ?#.sqlite'
   for connect in [common.readonly_sqlite,compact_search.connect,enrich.connect]:
    with self.assertRaises(sqlite3.OperationalError):connect(p)
   self.assertFalse(p.exists())
 def test_catalog_travel_paths(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/'travel ?#%.sqlite';d=sqlite3.connect(p)
   d.executescript('CREATE TABLE page(id,title,revision,timestamp,redirect,wikitext_zlib);CREATE TABLE listing(page,ordinal,lat,lon,name);')
   d.execute('INSERT INTO page VALUES(1,\'Demo\',99,\'2026-01-01\',NULL,?)',(zlib.compress(b'Original text'),));d.execute("INSERT INTO listing VALUES(1,0,0,0,'Cafe')");d.commit();d.close()
   c=catalog.Catalog([],None,None,p)
   self.assertEqual(c.travel('Demo')[0]['revision'],99)
   self.assertEqual(c.travel_source(1)['wikitext'],'Original text')
   self.assertEqual(c.travel_nearby(0,0,1)[0]['name'],'Cafe')
 def test_legacy_search_path(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/'places ?#.sqlite';d=sqlite3.connect(p)
   d.executescript('CREATE TABLE place(id,name,lat,lon,category,city,country,confidence,status,entity_key,gy,gx);');d.commit();d.close()
   self.assertEqual(search.search([p],0,0,1),[])

class Inflate(unittest.TestCase):
 def valid(self,obj):
  raw=json.dumps(obj,ensure_ascii=False).encode();return zlib.compress(raw),hashlib.sha256(raw).hexdigest()
 def test_valid_unicode(self):self.assertEqual(compact_search.inflate(*self.valid(['Café',{'id':9}])),['Café',{'id':9}])
 def test_hash(self):
  data,sha=self.valid([1])
  with self.assertRaises(ValueError):compact_search.inflate(data,'0'*64)
 def test_corrupt(self):
  with self.assertRaises(ValueError):compact_search.inflate(b'not zlib','0'*64)
 def test_truncated(self):
  data,sha=self.valid([1,2])
  with self.assertRaises(ValueError):compact_search.inflate(data[:-2],sha)
 def test_trailing(self):
  data,sha=self.valid([1])
  for suffix in [b'x',zlib.compress(b'[]')]:
   with self.assertRaises(ValueError):compact_search.inflate(data+suffix,sha)
 def test_compressed_limit(self):
  self.assertEqual(compact_search.MAX_COMPRESSED,1048576)
  data,sha=self.valid([base64.b64encode(random.Random(9821).randbytes(1200000)).decode()])
  self.assertGreater(len(data),1048576)
  with self.assertRaises(ValueError):compact_search.inflate(data,sha)
 def test_inflation_bound(self):
  old=compact_search.MAX_BLOCK;compact_search.MAX_BLOCK=512
  try:
   with self.assertRaises(ValueError):compact_search.inflate(*self.valid(['x'*1024]))
  finally:compact_search.MAX_BLOCK=old
 def test_json_invalid(self):
  raw=b'{broken'
  with self.assertRaises(ValueError):compact_search.inflate(zlib.compress(raw),hashlib.sha256(raw).hexdigest())

class Atomic(unittest.TestCase):
 def test_unicode_and_replace(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/'evidence.json';p.write_text('{"old":true}')
   common.atomic_json(p,{'name':'İstanbul','n':42});self.assertEqual(json.loads(p.read_text()),{'name':'İstanbul','n':42});self.assertEqual([x.name for x in pathlib.Path(tmp).iterdir()],['evidence.json'])
 def test_serialization_failure_preserves_old(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/'evidence.json';p.write_bytes(b'original');before=list(pathlib.Path(tmp).iterdir())
   with self.assertRaises(TypeError):common.atomic_json(p,object())
   self.assertEqual(p.read_bytes(),b'original');self.assertEqual(list(pathlib.Path(tmp).iterdir()),before)
 def test_replace_failure_cleans_own_temp(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);target=root/'directory.json';target.mkdir();keep=root/'keep.tmp';keep.write_text('unrelated')
   with self.assertRaises(OSError):common.atomic_json(target,{'new':True})
   self.assertEqual({p.name for p in root.iterdir()},{'directory.json','keep.tmp'});self.assertEqual(keep.read_text(),'unrelated')
 def test_concurrent_writers(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);p=root/'evidence.json'
   with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
    jobs=[pool.submit(common.atomic_json,p,{'writer':n,'data':'x'*10000}) for n in range(120)]
    for job in jobs:job.result()
   result=json.loads(p.read_text());self.assertIn(result['writer'],range(120));self.assertEqual(result['data'],'x'*10000);self.assertEqual({x.name for x in root.iterdir()},{'evidence.json'})
 def test_hash_norm_regressions(self):
  self.assertEqual(common.norm('  ＣＡＦＥ  É '),'cafe é')
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/'a';p.write_bytes(b'abc');self.assertEqual(common.file_sha256(p),hashlib.sha256(b'abc').hexdigest())

class Filters(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=pathlib.Path(self.tmp.name);self.p=root/'places.sqlite';self.o=root/'osm.sqlite'
  d=sqlite3.connect(self.p);d.executescript('CREATE TABLE block(id,records,payload,sha256);CREATE TABLE grid(gy,gx,block);CREATE TABLE category(category,block);CREATE TABLE city(city,block);')
  rows=[]
  for n,(name,city) in enumerate([('Café','North'),('Tea','North'),('Café','South')],1):
   r={'id':str(n),'names':{'primary':name},'taxonomy':{'primary':'cafe'},'addresses':[{'locality':city,'country':'ZZ'}]};rows.append([n,0,0,common.norm(name),r])
  raw=json.dumps(rows).encode();d.execute('INSERT INTO block VALUES(1,3,?,?)',(zlib.compress(raw),hashlib.sha256(raw).hexdigest()));d.execute('INSERT INTO grid VALUES(900,1800,1)');d.execute("INSERT INTO category VALUES('cafe',1)")
  for c in ['North','South']:d.execute('INSERT INTO city VALUES(?,1)',(c,))
  d.commit();d.close();d=sqlite3.connect(self.o);d.execute('CREATE TABLE osm(type,id,name_key,lat,lon,vegan,vegetarian,raw)');d.commit();d.close()
  self.c=catalog.Catalog([self.p],None,self.o,None)
 def tearDown(self):self.tmp.cleanup()
 def test_default_legacy_arguments(self):
  r=self.c.nearby(0,0,2,'cafe',None,5);self.assertEqual(len(r['snapshot_results']),2);self.assertEqual(r['source_family'],'Overture');self.assertIsNone(r['live_status'])
 def test_combined_filters(self):
  r=self.c.nearby(0,0,2,name='  CAFÉ ',city='North');self.assertEqual([x['id'] for x in r['snapshot_results']],['1'])
 def test_city_exact(self):self.assertEqual(self.c.nearby(0,0,2,city='north')['snapshot_results'],[])
 def test_name_absence(self):self.assertEqual(self.c.nearby(0,0,2,name='Missing')['snapshot_results'],[])
 def test_diet_remains_separate(self):
  r=self.c.nearby(0,0,2,diet='vegan');self.assertEqual(r['source_family'],'OpenStreetMap');self.assertEqual(r['snapshot_results'],[])
 def test_diet_filter_joins_rejected(self):
  for kwargs in [{'name':'Café'},{'city':'North'},{'name':''},{'city':''},{'category':'cafe'}]:
   with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.c.nearby(0,0,2,diet='vegan',**kwargs)

classes={'paths':Paths,'inflate':Inflate,'atomic':Atomic,'filters':Filters}
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(classes[TASK]))
print('GRADE_JSON '+json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()}))
sys.exit(0 if result.wasSuccessful() else 1)
