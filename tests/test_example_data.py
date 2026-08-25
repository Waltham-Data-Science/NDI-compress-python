import unittest
import numpy as np
import os
import json
import pytest
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

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "16-bit method-21 digital decoder is wrong: the fixture "
            "data_binary.nbf.tgz payload IS byte-identical to data_binary.bin "
            "(the old skip reason was false); the C decoder emits 1000 bytes "
            "instead of 2000, so expand_digital now raises on the size "
            "mismatch. Fix lives in the (absent) codec source; when repaired "
            "this xpasses and flips this test red."
        ),
    )
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

    def test_expand_digital_raises_on_size_mismatch(self):
        # The 16-bit method-21 payload decodes to 1000 bytes but the header
        # (bits_per_sample=16, shape 100x10) implies 2000; expand_digital must
        # raise a ValueError naming both sizes rather than silently forcing
        # bits=8 and returning bit-unpacked garbage.
        filename = os.path.join(EXAMPLE_DATA_DIR, "data_binary.nbf.tgz")
        with self.assertRaises(ValueError) as ctx:
            ndi_compress.expand_digital(filename)
        msg = str(ctx.exception)
        self.assertIn("1000", msg)
        self.assertIn("2000", msg)

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

class TestRoundTripIdentity(unittest.TestCase):
    """compress-then-expand fidelity per codec (previously uncovered)."""

    def setUp(self):
        self.files_to_remove = []

    def tearDown(self):
        for f in self.files_to_remove:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

    def test_roundtrip_digital(self):
        data = np.random.randint(0, 2, size=(120, 8)).astype(np.uint8)
        filename = "rt_digital"
        self.files_to_remove.append(filename + ".nbf.tgz")
        ndi_compress.compress_digital(data, filename)
        out, _, _ = ndi_compress.expand_digital(filename + ".nbf.tgz")
        np.testing.assert_array_equal(out, data)

    def test_roundtrip_ephys(self):
        col = (np.sin(np.linspace(0, 10, 500)) * 1000).astype(np.int16)
        data = np.column_stack([col, col[::-1]])
        filename = "rt_ephys"
        self.files_to_remove.append(filename + ".nbf.tgz")
        ndi_compress.compress_ephys(data, filename)
        out, _ = ndi_compress.expand_ephys(filename + ".nbf.tgz")
        np.testing.assert_allclose(out, data.astype(np.float64), atol=1e-7)

    def test_roundtrip_time(self):
        data = np.linspace(0, 5, 300)[:, np.newaxis]
        filename = "rt_time"
        self.files_to_remove.append(filename + ".nbf.tgz")
        ndi_compress.compress_time(data, filename)
        out = ndi_compress.expand_time(filename + ".nbf.tgz")
        np.testing.assert_allclose(out, data, atol=1e-9)


if __name__ == '__main__':
    unittest.main()
