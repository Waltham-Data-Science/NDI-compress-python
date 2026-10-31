# NDI Compress Python

This is a Python wrapper for the NDI Compression tools.

## Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

This package requires the NDI compression C executables to be present.
By default, it looks for them in `../../C/bin` relative to the `ndi_compress` package file.
You can override this by setting the `NDI_BIN_PATH` environment variable.

```python
import ndi_compress
import numpy as np

# Create some data
data = np.random.randint(0, 2, size=(100, 10)).astype(np.uint8)

# Compress
ndi_compress.compress_digital(data, "my_data")

# Expand
data_out, ratio, output_files = ndi_compress.expand_digital("my_data.nbf.tgz")
```

## The bundled executables

The compression tools are C programs from
[NDI-compress](https://github.com/Waltham-Data-Science/NDI-compress). This
package ships them prebuilt in `src/ndicompress/bin/{linux,macos,windows}`, so
nothing is compiled on install. `ndi-compress-ref.txt` names the NDI-compress
commit they were built from.

To update them after NDI-compress changes, either change
`ndi-compress-ref.txt` to the new commit (or to a branch or tag name) and
push, or run the **Build binaries
from NDI-compress** workflow (Actions tab), optionally naming a branch, tag or
commit. The workflow builds the tools on Linux, macOS (universal) and Windows,
runs this package's tests with them on each, and commits them, with the updated
`ndi-compress-ref.txt`, to the branch it ran on. A commit made by a workflow starts no
other workflow, so afterwards run **Test NDI Compress** on that branch from the
Actions tab (or push anything) to test the new head.

NDI-compress is private, so the workflow reads it with a read-only deploy key:
add the public key to NDI-compress (Settings > Deploy keys, without write
access) and store the private key as this repository's Actions secret
`NDI_COMPRESS_DEPLOY_KEY`.
