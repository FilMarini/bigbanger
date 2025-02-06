"""
Repository: https://github.com/FilMarini/bigbanger
License: Apache License, Version 2.0

Notes:
This file is part of an open-source project. Feel free to contribute or report issues on the project's repository.

"""

def byte_length(n):
    if n == 0:
        return 1  # Even 0 requires at least 1 byte
    bytes_count = 0
    while n:
        n >>= 8  # Shift 8 bits (1 byte) at a time
        bytes_count += 1
    return bytes_count
