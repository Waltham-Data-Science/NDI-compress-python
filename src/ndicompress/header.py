import struct
import os

def read_ndi_header(nbh_file_path):
    """
    Reads the NDI binary header file (.nbh) and returns a dictionary of parameters.
    """
    params = {}
    with open(nbh_file_path, 'rb') as f:
        # 1. Read Fixed Header (100 bytes)
        fixed_header_bytes = f.read(100)
        if len(fixed_header_bytes) < 100:
            raise ValueError("File too short for NDI header")

        magic = fixed_header_bytes[0:15].decode('ascii')
        if magic != "NDIBINARYHEADER":
            raise ValueError(f"Invalid magic string: {magic}")

        # The next 10 uint32s start at offset 15.
        # 10 * 4 = 40 bytes.
        # But wait, `write_ndibinary` writes 15 chars, then uint32s.
        # Does it align?
        # fwrite(..., 'char') -> 1 byte.
        # So offset is 15.

        fixed_fmt = '<10I' # Little-endian, 10 unsigned ints
        fixed_values = struct.unpack_from(fixed_fmt, fixed_header_bytes, 15)

        params['ndi_binary_version'] = fixed_values[0]
        params['encode_method'] = fixed_values[1]
        params['payload_format'] = fixed_values[2]
        params['payload_isunsigned'] = fixed_values[3]
        params['payload_bits_per_sample'] = fixed_values[4]
        params['payload_rows'] = fixed_values[5]
        params['payload_columns'] = fixed_values[6]
        params['original_format'] = fixed_values[7]
        params['original_isunsigned'] = fixed_values[8]
        params['original_bits_per_sample'] = fixed_values[9]

        # 2. Read Variable Header
        # The file pointer for `f` is at 100 because we read 100 bytes.
        # The variable portion starts at 100.

        method = params['encode_method']

        if method == 21: # Digital
            # fwrite(fid_header,num_digital_channels,'uint32');
            data = f.read(4)
            params['num_digital_channels'] = struct.unpack('<I', data)[0]

            # Infer original dimensions
            params['original_rows'] = params['payload_rows']
            params['original_columns'] = params['num_digital_channels']

        elif method == 1: # Ephys
            # fwrite(fid_header,code_r,'uint32');
            # fwrite(fid_header,code_c,'uint32');
            data = f.read(8)
            code_r, code_c = struct.unpack('<II', data)
            params['code_rows'] = code_r
            params['code_columns'] = code_c

            # fwrite(fid_header,code,'double'); -> code_r * code_c doubles
            code_size = code_r * code_c * 8
            code_data = f.read(code_size)
            # code is stored column-major? or whatever fwrite does.
            # Assuming row-major read into flat array or use numpy if needed,
            # but for now just skipping or reading as list.
            # We don't strictly need 'code' for uncompress call (it's in the file for reconstruction).
            # But wait, expand_ephys needs 'code' if it does manual reconstruction?
            # C uncompress tool reads it internally.
            # Python 'expand_ephys' just calls C tool.
            # So we just need to read past it?
            # Or do we need 'original_rows/cols'?

            # Note: For method 1, payload dimensions == original dimensions usually?
            # compress_ephys.m: payload_rows = s, payload_columns = c.
            params['original_rows'] = params['payload_rows']
            params['original_columns'] = params['payload_columns']

        elif method == 61: # Time
            # fwrite(fid_header,initial_data,'double');
            # initial_data size?
            # In compress_time: initial_data is [2 x C].
            # C is payload_columns.
            C = params['payload_columns']
            init_data_size = 2 * C * 8
            f.read(init_data_size) # skip

            # Infer original dimensions
            # Time method reduces S rows to S-1 rows.
            params['original_rows'] = params['payload_rows'] + 1
            params['original_columns'] = params['payload_columns']

        elif method == 41: # EventMarkText
            # fwrite(fid_header,[edd_r edd_c],'uint32');
            data = f.read(8)
            edd_r, edd_c = struct.unpack('<II', data)
            params['edd_rows'] = edd_r
            params['edd_columns'] = edd_c

            # fwrite(fid_header,event_data_description,'double');
            edd_size = edd_r * edd_c * 8
            f.read(edd_size) # skip

            # Original dims?
            # EventMarkText data is not a simple matrix.
            # But the C tool outputs JSON.
            pass

        elif method == 2: # Metadata
             # Metadata method has no variable parameters in header?
             # write_ndibinary.m case 2: "nothing needed"
             pass
        else:
            # Maybe just pass through or warn.
            pass

    return params
