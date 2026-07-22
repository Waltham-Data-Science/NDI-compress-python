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

The installed package is imported as `ndicompress`.

This package requires the NDI compression C executables to be present.
By default, it looks for them under `bin/<platform>` (e.g. `bin/macos`)
inside the installed `ndicompress` package. You can override the location by
setting the `NDI_BIN_PATH` environment variable to a directory containing the
executables (useful for pointing at a locally rebuilt codec).

Each codec executable runs in a subprocess with a timeout (default 300 seconds)
so a hung or looping codec process cannot block indefinitely. Override it with
the `NDI_COMPRESS_TIMEOUT` environment variable (in seconds); a value that is
non-positive or unparseable falls back to the default with a warning. The
variable is read on each codec call, so it can be changed at runtime after
import.

```python
import ndicompress
import numpy as np

# Create some binary data (compress_digital accepts only 0/1 or bool input)
data = np.random.randint(0, 2, size=(100, 10)).astype(np.uint8)

# Compress -> returns (ratio, None, None)
ratio, _, _ = ndicompress.compress_digital(data, "my_data")

# Expand -> returns (data, None, params)
data_out, _, params = ndicompress.expand_digital("my_data.nbf.tgz")
```
