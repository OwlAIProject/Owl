wav_header_size = 44

def create_wav_header(sample_bytes: int, sample_rate: int, sample_bits: int = 16, num_channels: int = 1) -> bytes:
    sample_bytes = int(sample_bytes)
    sample_rate = int(sample_rate)
    sample_bits = int(sample_bits)
    num_channels = int(num_channels)
    
    assert sample_bits % 8 == 0
    bytes_per_sample = int(sample_bits / 8)
    header_size = 44
    file_size = header_size - 8 + sample_bytes
    byte_rate = sample_rate * bytes_per_sample

    header = \
        b"RIFF" + \
        file_size.to_bytes(4, byteorder="little") + \
        b"WAVE" + \
        b"fmt " + \
        b"\x10\x00\x00\x00" + \
        b"\x01\x00" + \
        num_channels.to_bytes(2, byteorder="little") + \
        sample_rate.to_bytes(4, byteorder="little") + \
        byte_rate.to_bytes(4, byteorder="little") + \
        bytes_per_sample.to_bytes(2, byteorder="little") + \
        sample_bits.to_bytes(2, byteorder="little") + \
        b"data" + \
        sample_bytes.to_bytes(4, byteorder="little")
    return header