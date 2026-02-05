import unittest
import numpy as np
import os
import json
import ndicompress as ndi_compress

# Path to example data
EXAMPLE_DATA_DIR = os.path.join(os.path.dirname(__file__), "example-data")

class TestExampleData(unittest.TestCase):

    def test_expand_digital(self):
        filename = os.path.join(EXAMPLE_DATA_DIR, "data_digital.nbf.tgz")
        raw_bin = os.path.join(EXAMPLE_DATA_DIR, "data_digital.bin")
        raw_json = os.path.join(EXAMPLE_DATA_DIR, "data_digital.json")

        # Read expected dims
        with open(raw_json, 'r') as f:
            meta = json.load(f)
        shape = tuple(meta['size']) # [500, 16]

        # Read expected data (stored as uint8, column-major usually in these tests?)
        # The json says "filename": "data_digital.bin", "dtype": "uint8"
        # Let's assume the .bin is raw bytes.
        expected_data = np.fromfile(raw_bin, dtype=np.uint8).reshape(shape, order='F')

        # Expand
        data_out, _, _ = ndi_compress.expand_digital(filename)

        # Compare
        np.testing.assert_array_equal(data_out, expected_data)

    @unittest.skip("Example data mismatch: data_binary.nbf.tgz content does not match data_binary.bin")
    def test_expand_digital_int16(self):
        # Maps to data_binary
        filename = os.path.join(EXAMPLE_DATA_DIR, "data_binary.nbf.tgz")
        raw_bin = os.path.join(EXAMPLE_DATA_DIR, "data_binary.bin")
        raw_json = os.path.join(EXAMPLE_DATA_DIR, "data_binary.json")

        with open(raw_json, 'r') as f:
            meta = json.load(f)
        shape = tuple(meta['size']) # [100, 10]

        # data_binary is Method 21 (Digital) but int16
        expected_data = np.fromfile(raw_bin, dtype=np.int16).reshape(shape, order='F')

        data_out, _, _ = ndi_compress.expand_digital(filename)

        np.testing.assert_array_equal(data_out, expected_data)

    def test_expand_time(self):
        filename = os.path.join(EXAMPLE_DATA_DIR, "data_time.nbf.tgz")
        raw_bin = os.path.join(EXAMPLE_DATA_DIR, "data_time.bin")
        raw_json = os.path.join(EXAMPLE_DATA_DIR, "data_time.json")

        with open(raw_json, 'r') as f:
            meta = json.load(f)
        shape = tuple(meta['size'])

        expected_data = np.fromfile(raw_bin, dtype=np.float64).reshape(shape, order='F')

        data_out = ndi_compress.expand_time(filename)

        # Compare with tolerance
        np.testing.assert_allclose(data_out, expected_data, atol=1e-9)

    def test_expand_metadata(self):
        filename = os.path.join(EXAMPLE_DATA_DIR, "data_metadata.nbf.tgz")
        raw_json = os.path.join(EXAMPLE_DATA_DIR, "data_metadata.json")

        with open(raw_json, 'r') as f:
            expected_data = json.load(f)

        data_out = ndi_compress.expand_metadata(filename)

        self.assertEqual(data_out, expected_data)

    def test_expand_eventmarktext(self):
        filename = os.path.join(EXAMPLE_DATA_DIR, "data_eventmarktext.nbf.tgz")
        raw_json = os.path.join(EXAMPLE_DATA_DIR, "data_eventmarktext.json")

        with open(raw_json, 'r') as f:
            expected_full = json.load(f)

        # The expected full json has channeltypes, channel, T, D keys

        ct_out, ch_out, T_out, D_out = ndi_compress.expand_eventmarktext(filename)

        self.assertEqual(ct_out, expected_full['channeltypes'])
        self.assertEqual(ch_out, expected_full['channel'])

        # T and D can be complex lists
        # Just check basic equality
        # Note: T might come out as list of lists or similar
        # JSON loading might give slightly different types (e.g. list vs tuple)
        # But here both are from JSON or JSON-like process

        # Deep compare T (list of lists of floats)
        # D (list of lists of mixed types?)
        for t1, t2 in zip(T_out, expected_full['T']):
            np.testing.assert_allclose(t1, t2, rtol=1e-10)

        self.assertEqual(D_out, expected_full['D'])

if __name__ == '__main__':
    unittest.main()
