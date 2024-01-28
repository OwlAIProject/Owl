import os

wav_header_size = 44

def create_wav_header(num_sample_bytes: int, sample_rate: int, sample_bits: int = 16, num_channels: int = 1) -> bytes:
    num_sample_bytes = int(num_sample_bytes)
    sample_rate = int(sample_rate)
    sample_bits = int(sample_bits)
    num_channels = int(num_channels)
    
    assert sample_bits % 8 == 0
    bytes_per_sample = int(sample_bits / 8)
    header_size = 44
    file_size = header_size - 8 + num_sample_bytes
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
        num_sample_bytes.to_bytes(4, byteorder="little")
    return header

def append_to_wav_file(filepath: str, sample_bytes: bytes, sample_rate: int, sample_bits: int = 16, num_channels: int = 1) -> int:
    """
    Appends sample bytes to a WAV file and updates the header. If the file is empty, will create the
    initial header. The sample rate, bits, and number of channels must remain consistent throughout
    the file and it is up to the caller to enforce this. The existing file header will not be
    checked against the incoming data.

    Parameters
    ----------
    filepath : str
        File to append to. A new file will be created if none exists.
    sample_bytes : bytes
        Sample bytes to append.
    sample_rate : int
        Sample rate in Hz.
    sample_bits : int
        Sample bit width.
    num_channels : int
        Number of channels.
    
    Returns
    -------
    int
        Sample bytes written to end of file. Excludes number of header bytes written.
    """
    write_mode = "r+b" if os.path.exists(path=filepath) else "wb"
    with open(file=filepath, mode=write_mode) as fp:
        # Count existing number of samples in file, if any
        fp.seek(0, 2)       # seek to end to get size
        existing_sample_bytes = max(0, fp.tell() - wav_header_size)

        # Write a header that reflects existing samples and ones we are about to add
        added_sample_bytes = len(sample_bytes)
        header = create_wav_header(
            num_sample_bytes=existing_sample_bytes + added_sample_bytes,
            sample_rate=sample_rate,
            sample_bits=sample_bits,
            num_channels=num_channels
        )
        fp.seek(0)          # beginning of file
        fp.write(header)    # overwrite header with new

        # Move back to the end of the file and append new samples
        fp.seek(0, 2) 
        bytes_written = fp.write(sample_bytes)
        return bytes_written
        