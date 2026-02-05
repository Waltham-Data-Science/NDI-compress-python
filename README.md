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
