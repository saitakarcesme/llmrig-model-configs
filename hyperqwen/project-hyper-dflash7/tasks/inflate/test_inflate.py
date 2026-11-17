"""Standard-library unittest regressions for the hardened compact_search.inflate decoder."""
import hashlib,json,unittest,zlib
from compact_search import inflate,MAX_BLOCK,MAX_COMPRESSED

def make_block(obj,ensure_ascii=False):
 """Return (zlib payload, sha256 hex of the raw JSON, raw bytes) for a JSON object."""
 raw=json.dumps(obj,ensure_ascii=ensure_ascii).encode('utf-8')
 return zlib.compress(raw),hashlib.sha256(raw).hexdigest(),raw

def make_raw_block(raw):
 """Return (zlib payload, sha256 hex) for arbitrary raw bytes."""
 return zlib.compress(raw),hashlib.sha256(raw).hexdigest()

class InflateBoundTests(unittest.TestCase):
 def test_compressed_bound_is_one_mib(self):
  self.assertEqual(MAX_COMPRESSED,1024*1024)
  self.assertEqual(MAX_BLOCK,32*1024*1024)
 def test_compressed_bound_checked_before_decoding(self):
  # Not valid zlib at all: the 1 MiB bound must fire before any decoding is attempted.
  payload=b'\x00'*(MAX_COMPRESSED+1)
  with self.assertRaises(ValueError) as ctx:
   inflate(payload,'0'*64)
  self.assertIn('1 MiB',str(ctx.exception))
 def test_compressed_bound_inclusive_at_exactly_one_mib(self):
  # Exactly 1 MiB passes the bound check and fails later as corrupt zlib.
  payload=b'\x00'*MAX_COMPRESSED
  with self.assertRaises(ValueError) as ctx:
   inflate(payload,'0'*64)
  self.assertIn('zlib',str(ctx.exception))
 def test_non_bytes_payload_rejected(self):
  with self.assertRaises(ValueError):
   inflate('{"id":"x"}','0'*64)

class InflateCorruptZlibTests(unittest.TestCase):
 def test_corrupt_header(self):
  compressed,sha,_=make_block({'id':'c1'})
  bad=b'\x05'+compressed[1:]  # invalid CMF byte
  with self.assertRaises(ValueError) as ctx:
   inflate(bad,sha)
  self.assertIn('zlib',str(ctx.exception))
 def test_corrupt_checksum(self):
  compressed,sha,_=make_block({'id':'c2'})
  bad=compressed[:-1]+bytes([compressed[-1]^0xff])
  with self.assertRaises(ValueError) as ctx:
   inflate(bad,sha)
  self.assertIn('zlib',str(ctx.exception))
 def test_truncated_stream(self):
  compressed,sha,_=make_block({'id':'t1','names':{'primary':'A'*100}})
  with self.assertRaises(ValueError):
   inflate(compressed[:-3],sha)  # cut into the 4-byte Adler-32 checksum
 def test_heavily_truncated_stream(self):
  compressed,sha,_=make_block({'id':'t2','names':{'primary':'A'*1000}})
  with self.assertRaises(ValueError):
   inflate(compressed[:len(compressed)//2],sha)

class InflateStreamShapeTests(unittest.TestCase):
 def test_trailing_garbage(self):
  compressed,sha,_=make_block({'id':'g1'})
  with self.assertRaises(ValueError):
   inflate(compressed+b'GARBAGE',sha)
 def test_concatenated_streams(self):
  c1,sha1,_=make_block({'id':'s1'})
  c2,_,_=make_block({'id':'s2'})
  with self.assertRaises(ValueError):
   inflate(c1+c2,sha1)

class InflateIntegrityTests(unittest.TestCase):
 def test_wrong_sha256(self):
  compressed,sha,_=make_block({'id':'h1'})
  wrong=('0' if sha[0]!='0' else '1')+sha[1:]
  with self.assertRaises(ValueError) as ctx:
   inflate(compressed,wrong)
  self.assertIn('hash',str(ctx.exception))
 def test_invalid_json(self):
  compressed,sha=make_raw_block(b'this is not json')
  with self.assertRaises(ValueError) as ctx:
   inflate(compressed,sha)
  self.assertIn('JSON',str(ctx.exception))
 def test_invalid_utf8(self):
  compressed,sha=make_raw_block(b'\xff\xfe\x00bad')
  with self.assertRaises(ValueError) as ctx:
   inflate(compressed,sha)
  self.assertIn('JSON',str(ctx.exception))

class InflateInflatedBoundTests(unittest.TestCase):
 def test_inflated_bound_exceeded(self):
  raw=b'A'*(MAX_BLOCK+1)  # compresses to ~32 KiB, far below the 1 MiB compressed bound
  compressed,sha=make_raw_block(raw)
  self.assertLess(len(compressed),MAX_COMPRESSED)
  with self.assertRaises(ValueError) as ctx:
   inflate(compressed,sha)
  self.assertIn('oversized',str(ctx.exception))
 def test_inflated_bound_inclusive_at_exactly_32_mib(self):
  raw=b'A'*MAX_BLOCK  # exactly 32 MiB: passes the size check, fails later at JSON
  compressed,sha=make_raw_block(raw)
  self.assertLess(len(compressed),MAX_COMPRESSED)
  with self.assertRaises(ValueError) as ctx:
   inflate(compressed,sha)
  self.assertNotIn('oversized',str(ctx.exception))
  self.assertIn('JSON',str(ctx.exception))

class InflateValidRoundTripTests(unittest.TestCase):
 def test_ascii_roundtrip(self):
  obj={'id':'x1','names':{'primary':'Cafe'},'basic_category':'cafe'}
  compressed,sha,_=make_block(obj,ensure_ascii=True)
  self.assertEqual(inflate(compressed,sha),obj)
 def test_unicode_roundtrip(self):
  obj={'id':'u1','names':{'primary':'Café 日本語 🍜'},'basic_category':'cafe',
       'addresses':[{'locality':'Zürich','country':'Suisse'}]}
  compressed,sha,_=make_block(obj,ensure_ascii=False)
  self.assertEqual(inflate(compressed,sha),obj)
 def test_bytearray_and_memoryview_roundtrip(self):
  obj={'id':'bv1','names':{'primary':'Böhm'}}
  compressed,sha,_=make_block(obj,ensure_ascii=False)
  self.assertEqual(inflate(bytearray(compressed),sha),obj)
  self.assertEqual(inflate(memoryview(compressed),sha),obj)
 def test_empty_container_roundtrip(self):
  for obj in ({},[],{'id':'e1','tags':{}}):
   compressed,sha,_=make_block(obj,ensure_ascii=False)
   self.assertEqual(inflate(compressed,sha),obj)

if __name__=='__main__':
 unittest.main(verbosity=2)
