import unittest
import numpy as np
import os
import shutil
import json
import sys

# Add parent dir to path to import ndi_compress
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import ndi_compress

class TestNDICompress(unittest.TestCase):
    def setUp(self):
        self.files_to_remove = []

    def tearDown(self):
        for f in self.files_to_remove:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

    def test_digital(self):
        S, C = 100, 10
        data = np.random.randint(0, 2, size=(S, C)).astype(np.uint8)
        filename = "test_digital"
        self.files_to_remove.append(filename + ".nbf.tgz")

        ratio, U, params_out = ndi_compress.compress_digital(data, filename)

        self.assertIsInstance(ratio, float)
        self.assertGreater(ratio, 0)

        data_out, U_out, params = ndi_compress.expand_digital(filename + ".nbf.tgz")

        self.assertTrue(np.array_equal(data, data_out))
        self.assertEqual(data_out.shape, (S, C))
        self.assertEqual(data_out.dtype, np.uint8)

    def test_ephys(self):
        S, C = 1000, 4
        t = np.linspace(0, 10, S)
        data = (np.sin(t) * 1000).astype(np.int16)
        data = np.column_stack([data] * C)

        filename = "test_ephys"
        self.files_to_remove.append(filename + ".nbf.tgz")

        ratio, D_R, D_E, code = ndi_compress.compress_ephys(data, filename)

        self.assertIsInstance(ratio, float)

        data_out, D_E_out = ndi_compress.expand_ephys(filename + ".nbf.tgz")

        diff = np.abs(data.astype(np.float64) - data_out)
        max_diff = np.max(diff)

        self.assertLess(max_diff, 1e-7)
        self.assertEqual(data_out.shape, (S, C))

    def test_time(self):
        S, C = 100, 1
        t = np.linspace(0, 10, S)
        data = t[:, np.newaxis]

        filename = "test_time"
        self.files_to_remove.append(filename + ".nbf.tgz")

        ratio, D_E, D_d = ndi_compress.compress_time(data, filename)
        self.assertIsInstance(ratio, float)

        data_out = ndi_compress.expand_time(filename + ".nbf.tgz")

        diff = np.abs(data - data_out)
        max_diff = np.max(diff)

        self.assertLess(max_diff, 1e-7)
        self.assertEqual(data_out.shape, (S, C))

    def test_metadata(self):
        data = {"key": "value", "list": [1, 2, 3]}
        filename = "test_metadata"
        self.files_to_remove.append(filename + ".nbf.tgz")

        ratio = ndi_compress.compress_metadata(data, filename)
        self.assertIsInstance(ratio, float)

        data_out = ndi_compress.expand_metadata(filename + ".nbf.tgz")
        self.assertEqual(data, data_out)

    def test_eventmarktext(self):
        ct = ["event", "marker", "text"]
        ch = [1, 1, 1]
        T = [[0.1, 0.2], [0.3, 0.4], [0.5]]
        D = [[1.0, 1.0], [10, 20], ["hello"]]

        filename = "test_evt"
        self.files_to_remove.append(filename + ".nbf.tgz")

        ratio, data_struct, data_desc = ndi_compress.compress_eventmarktext(ct, ch, T, D, filename)
        self.assertIsInstance(ratio, float)

        ct_out, ch_out, T_out, D_out = ndi_compress.expand_eventmarktext(filename + ".nbf.tgz")

        self.assertEqual(ct, ct_out)
        self.assertEqual(ch, ch_out)
        # Check T with tolerance? Or exact if simple
        # Check D types
        self.assertEqual(D[2], D_out[2]) # String match

        # Check numeric lists
        np.testing.assert_allclose(T[0], T_out[0])
        np.testing.assert_allclose(D[0], D_out[0])

if __name__ == '__main__':
    unittest.main()
