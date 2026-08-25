import io
import os
import struct
import tarfile

import pytest

import ndicompress as ndi_compress


def _valid_nbh_bytes():
    """A minimal but well-formed .nbh header (method 21 digital, 1x1)."""
    header = b"NDIBINARYHEADER"
    # 10 little-endian uint32s: version, encode_method(21), payload_format,
    # payload_isunsigned, payload_bits_per_sample, payload_rows,
    # payload_columns, original_format, original_isunsigned,
    # original_bits_per_sample.
    header += struct.pack("<10I", 1, 21, 0, 1, 8, 1, 1, 0, 1, 8)
    # Pad fixed header out to 100 bytes.
    header += b"\x00" * (100 - len(header))
    # method 21 variable header: num_digital_channels (uint32)
    header += struct.pack("<I", 1)
    return header


def _make_malicious_archive(path, member_name):
    """Build a .nbf.tgz whose .nbh member carries a traversal path name."""
    nbh_bytes = _valid_nbh_bytes()
    with tarfile.open(path, "w:gz") as tar:
        info = tarfile.TarInfo(name=member_name)
        info.size = len(nbh_bytes)
        tar.addfile(info, io.BytesIO(nbh_bytes))


@pytest.mark.parametrize(
    "expand_fn",
    [
        ndi_compress.expand_digital,
        ndi_compress.expand_ephys,
        ndi_compress.expand_time,
    ],
)
def test_expand_rejects_traversal_member(expand_fn, tmp_path):
    """A .nbh member named ../../escaped.nbh must never write outside temp.

    The expand_* codecs are expected to fail later (the C decode step will not
    find a real payload), but the security-critical assertion is that NO file
    is created outside the extraction temp dir at the escaped path.
    """
    archive = tmp_path / "malicious.nbf.tgz"
    _make_malicious_archive(str(archive), "../../escaped.nbh")

    # Sentinel: the traversal target relative to the archive location.
    escaped = tmp_path.parent / "escaped.nbh"
    if escaped.exists():
        escaped.unlink()

    # The call may raise (missing/garbage payload); that is fine. What must NOT
    # happen is the escaped file appearing on disk.
    try:
        expand_fn(str(archive))
    except Exception:
        pass

    assert not escaped.exists(), (
        f"path traversal wrote outside temp dir: {escaped} was created"
    )
