import unittest
import zlib
import json
import hashlib
from compact_search import inflate, MAX_COMPRESSED, MAX_BLOCK

class TestCompactSearchInflate(unittest.TestCase):
    def test_valid_inflate(self):
        # Create a simple JSON structure that matches expected format: list of 5-tuples
        # For simplicity, we'll just use a list of lists with dummy data.
        data = [[1, 10.0, 20.0, 'name', {'id': 1, 'names': {'primary': 'test'}}]]
        json_str = json.dumps(data)
        json_bytes = json_str.encode('utf-8')
        compressed = zlib.compress(json_bytes)
        sha = hashlib.sha256(json_bytes).hexdigest()
        result = inflate(compressed, sha)
        self.assertEqual(result, data)

    def test_compressed_payload_too_large(self):
        # Create a payload larger than MAX_COMPRESSED (1 MiB)
        large_payload = b'x' * (MAX_COMPRESSED + 1)
        with self.assertRaises(ValueError):
            inflate(large_payload, 'dummy')

    def test_truncated_zlib(self):
        # Create a valid compressed payload and truncate it.
        data = [[1, 10.0, 20.0, 'name', {'id': 1}]]
        json_str = json.dumps(data)
        json_bytes = json_str.encode('utf-8')
        compressed = zlib.compress(json_bytes)
        # Truncate the compressed data by removing the last 1 byte
        truncated = compressed[:-1]
        sha = hashlib.sha256(json_bytes).hexdigest()
        with self.assertRaises(ValueError):
            inflate(truncated, sha)

    def test_trailing_garbage(self):
        # Append extra data to a valid compressed payload.
        data = [[1, 10.0, 20.0, 'name', {'id': 1}]]
        json_str = json.dumps(data)
        json_bytes = json_str.encode('utf-8')
        compressed = zlib.compress(json_bytes)
        garbage = compressed + b'extra'
        sha = hashlib.sha256(json_bytes).hexdigest()
        with self.assertRaises(ValueError):
            inflate(garbage, sha)

    def test_concatenated_streams(self):
        # Concatenate two compressed streams.
        data1 = [[1, 10.0, 20.0, 'name', {'id': 1}]]
        data2 = [[2, 30.0, 40.0, 'name2', {'id': 2}]]
        json_str1 = json.dumps(data1)
        json_str2 = json.dumps(data2)
        json_bytes1 = json_str1.encode('utf-8')
        json_bytes2 = json_str2.encode('utf-8')
        compressed1 = zlib.compress(json_bytes1)
        compressed2 = zlib.compress(json_bytes2)
        concatenated = compressed1 + compressed2
        # The SHA256 we provide should match the first stream's decompressed data.
        sha = hashlib.sha256(json_bytes1).hexdigest()
        with self.assertRaises(ValueError):
            inflate(concatenated, sha)

    def test_wrong_sha256(self):
        data = [[1, 10.0, 20.0, 'name', {'id': 1}]]
        json_str = json.dumps(data)
        json_bytes = json_str.encode('utf-8')
        compressed = zlib.compress(json_bytes)
        wrong_sha = '0' * 64
        with self.assertRaises(ValueError):
            inflate(compressed, wrong_sha)

    def test_invalid_json(self):
        # Create a compressed payload that is not valid JSON.
        # We'll compress some random bytes.
        random_bytes = b'random'
        compressed = zlib.compress(random_bytes)
        sha = hashlib.sha256(random_bytes).hexdigest()
        with self.assertRaises(ValueError):
            inflate(compressed, sha)

    def test_unicode_json_roundtrip(self):
        # Create a JSON string with Unicode characters.
        data = [['тест', 10.0, 20.0, 'name', {'id': 1, 'names': {'primary': 'тест'}}]]
        json_str = json.dumps(data, ensure_ascii=False)
        json_bytes = json_str.encode('utf-8')
        compressed = zlib.compress(json_bytes)
        sha = hashlib.sha256(json_bytes).hexdigest()
        result = inflate(compressed, sha)
        self.assertEqual(result, data)

    def test_inflated_payload_too_large(self):
        # Create a payload that decompresses to more than MAX_BLOCK (32 MiB).
        # We'll create a string of 33 MiB of '0' characters.
        large_json_bytes = b'0' * (MAX_BLOCK + 1024 * 1024)  # 33 MiB
        sha = hashlib.sha256(large_json_bytes).hexdigest()
        compressed = zlib.compress(large_json_bytes)
        with self.assertRaises(ValueError):
            inflate(compressed, sha)

if __name__ == '__main__':
    unittest.main()