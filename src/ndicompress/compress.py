import os
import sys
import struct
import tempfile
import subprocess
import json
import numpy as np
import tarfile
from .header import read_ndi_header

from .utility import get_executable_path

# Maximum seconds to wait for a codec subprocess before treating it as hung.
# Compression/decompression of very large arrays can be slow, so this default is
# generous; override via the NDI_COMPRESS_TIMEOUT environment variable.
_C_EXEC_TIMEOUT = float(os.environ.get("NDI_COMPRESS_TIMEOUT", "300"))


def _call_c_exec(exec_name, args):
    exec_path = get_executable_path(exec_name)
    cmd = [exec_path] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_C_EXEC_TIMEOUT
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"C executable {exec_name} timed out after {_C_EXEC_TIMEOUT:g}s"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(f"C executable {exec_name} failed: {result.stderr}")
    return result.stdout

def _write_temp_bin_json(data, temp_dir):
    """
    Writes data to a temporary .bin file and dimensions to a .json file.
    Returns the path to the .bin file.
    """
    # Ensure data is numpy array
    if not isinstance(data, np.ndarray):
        data = np.array(data)

    bin_path = os.path.join(temp_dir, "input.bin")
    json_path = os.path.join(temp_dir, "input.json")

    # Write JSON dimensions
    rows, cols = data.shape
    with open(json_path, 'w') as f:
        json.dump({"size": [rows, cols]}, f)

    # Write Binary Data (Column-Major)
    # Numpy is Row-Major by default (C-order).
    # MATLAB is Column-Major (F-order).
    # The C tools expect Column-Major storage (e.g. all of col 0, then all of col 1).
    # So we should convert to F-order bytes.
    with open(bin_path, 'wb') as f:
        # tobytes('F') flattens in column-major order
        f.write(data.tobytes(order='F'))

    return bin_path

def compress_digital(data, fullfilename):
    """
    Compress digital (binary) multichannel data.

    Parameters
    ----------
    data : numpy.ndarray
        Shape (S, C), where S is samples and C is channels.
        Should contain 0s and 1s.
    fullfilename : str
        Output filename base (without .nbf.tgz extension).

    Returns
    -------
    ratio : float
        Compression ratio (output_size / input_size).
    U : None
        Placeholder for converted uint8 data (not returned in this implementation).
    parameters_out : dict
        Header parameters (placeholder/None in this version as C generates it).
    """
    if not isinstance(data, np.ndarray):
        data = np.array(data)

    # Ensure uint8 (0 or 1)
    data = (data != 0).astype(np.uint8)

    in_size = data.nbytes

    with tempfile.TemporaryDirectory() as temp_dir:
        bin_path = _write_temp_bin_json(data, temp_dir)

        # Call C executable
        # Usage: ndi_compress_digital <input_bin_file> <output_base_name>
        _call_c_exec("ndi_compress_digital", [bin_path, fullfilename])

    outfile = fullfilename + ".nbf.tgz"
    out_size = os.path.getsize(outfile) if os.path.exists(outfile) else 0
    ratio = float(out_size) / float(in_size) if in_size > 0 else 0.0

    return ratio, None, None # U and parameters not fully reconstructed here

def expand_digital(fullfilename):
    """
    Expand digital data from NDI binary file.

    Parameters
    ----------
    fullfilename : str
        Path to the .nbf.tgz file.

    Returns
    -------
    data : numpy.ndarray
        Shape (S, C), unpacked digital data (0s and 1s, uint8).
    U : None
    parameters : dict
    """
    # 1. Extract Header to get dimensions
    if not fullfilename.endswith('.nbf.tgz'):
        if not os.path.exists(fullfilename) and os.path.exists(fullfilename + '.nbf.tgz'):
            fullfilename += '.nbf.tgz'

    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract .nbh file
        with tarfile.open(fullfilename, "r:gz") as tar:
             # Find .nbh file
             nbh_member = None
             for member in tar.getmembers():
                 if member.name.endswith('.nbh') and not os.path.basename(member.name).startswith('._'):
                     nbh_member = member
                     break
             if not nbh_member:
                 raise ValueError("No .nbh file found in archive")

             tar.extract(nbh_member, path=temp_dir)
             nbh_path = os.path.join(temp_dir, nbh_member.name)

             # Parse header
             params = read_ndi_header(nbh_path)

        # 2. Call Uncompress
        # Usage: ndi_uncompress_digital <input> <output>
        out_bin = os.path.join(temp_dir, "output.bin")
        _call_c_exec("ndi_uncompress_digital", [fullfilename, out_bin])

        # 3. Read Output
        # Output is raw unpacked bytes (0 or 1)
        S = params['original_rows']
        C = params['original_columns']

        bits = params.get('original_bits_per_sample', 8)
        unsigned = params.get('original_isunsigned', 1)

        # Check if output size matches expected bits
        file_size = os.path.getsize(out_bin)
        expected_size = S * C * (bits // 8)

        if file_size != expected_size and file_size == S * C:
            # Fallback: Binary produced 8-bit data despite header indicating otherwise
            bits = 8

        if bits == 8:
            dtype = np.uint8 if unsigned else np.int8
        elif bits == 16:
            dtype = np.uint16 if unsigned else np.int16
        elif bits == 32:
            dtype = np.uint32 if unsigned else np.int32
        elif bits == 64:
            dtype = np.uint64 if unsigned else np.int64
        else:
            raise ValueError(f"Unsupported bits per sample: {bits}")

        raw_data = np.fromfile(out_bin, dtype=dtype)

        data = raw_data.reshape((S, C), order='F')

        return data, None, params

def compress_ephys(data, fullfilename):
    """
    Compress ephys data.

    Parameters
    ----------
    data : numpy.ndarray
        Shape (S, C). Should be convertible to int16.
    fullfilename : str
        Output filename base.

    Returns
    -------
    ratio : float
    D_R : None
    D_E : None
    code : None
    """
    if not isinstance(data, np.ndarray):
        data = np.array(data)

    # C executable expects int16 binary input
    data_int16 = data.astype(np.int16)
    in_size = data.nbytes

    with tempfile.TemporaryDirectory() as temp_dir:
        bin_path = _write_temp_bin_json(data_int16, temp_dir)
        _call_c_exec("ndi_compress_ephys", [bin_path, fullfilename])

    outfile = fullfilename + ".nbf.tgz"
    out_size = os.path.getsize(outfile) if os.path.exists(outfile) else 0
    ratio = float(out_size) / float(in_size) if in_size > 0 else 0.0

    return ratio, None, None, None

def expand_ephys(fullfilename):
    """
    Expand ephys data.

    Returns
    -------
    data : numpy.ndarray
        Shape (S, C), float64 (double).
    D_E : None (Error signal not explicitly returned)
    """
    if not fullfilename.endswith('.nbf.tgz'):
         if not os.path.exists(fullfilename) and os.path.exists(fullfilename + '.nbf.tgz'):
             fullfilename += '.nbf.tgz'

    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract .nbh file
        with tarfile.open(fullfilename, "r:gz") as tar:
             nbh_member = None
             for member in tar.getmembers():
                 if member.name.endswith('.nbh') and not os.path.basename(member.name).startswith('._'):
                     nbh_member = member
                     break
             if not nbh_member:
                 raise ValueError("No .nbh file found")
             tar.extract(nbh_member, path=temp_dir)
             nbh_path = os.path.join(temp_dir, nbh_member.name)
             params = read_ndi_header(nbh_path)

        out_bin = os.path.join(temp_dir, "output.bin")
        _call_c_exec("ndi_uncompress_ephys", [fullfilename, out_bin])

        # Output is double (float64)
        S = params['original_rows']
        C = params['original_columns']

        raw_data = np.fromfile(out_bin, dtype=np.float64)
        data = raw_data.reshape((S, C), order='F')

        return data, None

def compress_time(data, fullfilename):
    """
    Compress time data.

    Parameters
    ----------
    data : numpy.ndarray
        Shape (S, C) or (S,). Double precision.
    fullfilename : str
        Output filename base.

    Returns
    -------
    ratio : float
    D_E : None
    D_d : None
    """
    if not isinstance(data, np.ndarray):
        data = np.array(data)

    if data.ndim == 1:
        data = data[:, np.newaxis]

    data = data.astype(np.float64)
    in_size = data.nbytes

    with tempfile.TemporaryDirectory() as temp_dir:
        bin_path = _write_temp_bin_json(data, temp_dir)
        _call_c_exec("ndi_compress_time", [bin_path, fullfilename])

    outfile = fullfilename + ".nbf.tgz"
    out_size = os.path.getsize(outfile) if os.path.exists(outfile) else 0
    ratio = float(out_size) / float(in_size) if in_size > 0 else 0.0

    return ratio, None, None

def expand_time(fullfilename):
    """
    Expand time data.

    Returns
    -------
    data : numpy.ndarray
        Shape (S, C), float64.
    """
    if not fullfilename.endswith('.nbf.tgz'):
         if not os.path.exists(fullfilename) and os.path.exists(fullfilename + '.nbf.tgz'):
             fullfilename += '.nbf.tgz'

    with tempfile.TemporaryDirectory() as temp_dir:
        with tarfile.open(fullfilename, "r:gz") as tar:
             nbh_member = None
             for member in tar.getmembers():
                 if member.name.endswith('.nbh') and not os.path.basename(member.name).startswith('._'):
                     nbh_member = member
                     break
             if not nbh_member:
                 raise ValueError("No .nbh file found")
             tar.extract(nbh_member, path=temp_dir)
             nbh_path = os.path.join(temp_dir, nbh_member.name)
             params = read_ndi_header(nbh_path)

        out_bin = os.path.join(temp_dir, "output.bin")
        _call_c_exec("ndi_uncompress_time", [fullfilename, out_bin])

        S = params['original_rows']
        C = params['original_columns']

        raw_data = np.fromfile(out_bin, dtype=np.float64)
        data = raw_data.reshape((S, C), order='F')

        return data

def compress_metadata(data, fullfilename):
    """
    Compress metadata (JSON serializable object).

    Parameters
    ----------
    data : dict or list
        Data to compress.
    fullfilename : str
        Output filename base.

    Returns
    -------
    ratio : float
    """
    # Create temp file just to measure size?
    # Or just assume in_size is string length?
    json_str = json.dumps(data)
    in_size = len(json_str)

    with tempfile.TemporaryDirectory() as temp_dir:
        json_path = os.path.join(temp_dir, "input.json")
        with open(json_path, 'w') as f:
            f.write(json_str)

        _call_c_exec("ndi_compress_metadata", [json_path, fullfilename])

    outfile = fullfilename + ".nbf.tgz"
    out_size = os.path.getsize(outfile) if os.path.exists(outfile) else 0
    ratio = float(out_size) / float(in_size) if in_size > 0 else 0.0
    return ratio

def expand_metadata(fullfilename):
    """
    Expand metadata.

    Returns
    -------
    data : dict or list
        Decompressed JSON data.
    """
    if not fullfilename.endswith('.nbf.tgz'):
         if not os.path.exists(fullfilename) and os.path.exists(fullfilename + '.nbf.tgz'):
             fullfilename += '.nbf.tgz'

    with tempfile.TemporaryDirectory() as temp_dir:
        out_file = os.path.join(temp_dir, "output.json")
        _call_c_exec("ndi_uncompress_metadata", [fullfilename, out_file])

        with open(out_file, 'r') as f:
            data = json.load(f)

        return data

def compress_eventmarktext(channeltype, channel, T, D, fullfilename):
    """
    Compress event, marker, and text data.

    Parameters
    ----------
    channeltype : list of str
    channel : list of int
    T : list of list of float
    D : list of list
    fullfilename : str

    Returns
    -------
    ratio : float
    data_struct : dict
    data_description : list
    """
    data = {
        "channeltypes": channeltype,
        "channel": channel,
        "T": T,
        "D": D
    }

    # Approx in_size
    json_str = json.dumps(data)
    in_size = len(json_str)

    with tempfile.TemporaryDirectory() as temp_dir:
        json_path = os.path.join(temp_dir, "input.json")
        with open(json_path, 'w') as f:
            f.write(json_str)

        _call_c_exec("ndi_compress_eventmarktext", [json_path, fullfilename])

    outfile = fullfilename + ".nbf.tgz"
    out_size = os.path.getsize(outfile) if os.path.exists(outfile) else 0
    ratio = float(out_size) / float(in_size) if in_size > 0 else 0.0

    return ratio, data, None

def expand_eventmarktext(fullfilename):
    """
    Expand event/mark/text data.

    Returns
    -------
    tuple : (channeltype, channel, T, D)
    """
    if not fullfilename.endswith('.nbf.tgz'):
         if not os.path.exists(fullfilename) and os.path.exists(fullfilename + '.nbf.tgz'):
             fullfilename += '.nbf.tgz'

    with tempfile.TemporaryDirectory() as temp_dir:
        out_file = os.path.join(temp_dir, "output.json")
        _call_c_exec("ndi_uncompress_eventmarktext", [fullfilename, out_file])

        with open(out_file, 'r') as f:
            data = json.load(f)

        return (data['channeltypes'], data['channel'], data['T'], data['D'])
