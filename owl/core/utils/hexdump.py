def hexdump(bytes, bytes_per_line = 16, offset_size = 2):
    """
    Prints a byte buffer as a human-readable hexadecimal dump.

    Parameters
    ----------
    bytes : bytes
        Buffer to dump.
    bytes_per_line : int
        How many bytes to print per line.
    offset_size : int
        Size of the location offset in the byte buffer in bytes. For example, if the buffer is less
        than 256 bytes, the offset need only be one byte long and can be set to 1. The offset is 
        printed at the beginning of each line
        as a hexadecimal number with number of digits equal to twice offset_size.
    """
    offset_mask = int.from_bytes(bytes = [ 0xff ] * offset_size, byteorder = "big")
    offset_format = "%%0%dx" % (offset_size * 2)
    start = 0
    while start < len(bytes):
        end = min(start + 16, len(bytes))
        hex_output = " ".join([ ("%02x" % bytes[start + j]) for j in range(end - start) ])
        ascii_output = "".join([ ("%c" % bytes[start + j] if chr(bytes[start + j]).isprintable() else ".") for j in range(end - start) ])
        expected_hex_line_length = 3 * bytes_per_line
        hex_padding = " " * (expected_hex_line_length - len(hex_output))
        ascii_padding = " " * (bytes_per_line - len(ascii_output))
        offset = offset_format % (start & offset_mask)
        print("%s:  %s%s [ %s%s ]" % (offset, hex_output, hex_padding, ascii_output, ascii_padding))
        start += bytes_per_line