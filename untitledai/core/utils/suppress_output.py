import contextlib
import os
import sys


@contextlib.contextmanager
def suppress_output():
    # Redirect stdout and stderr to /dev/null
    with open(os.devnull, 'w') as devnull:
        original_stdout, original_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = devnull, devnull
        try:
            yield
        finally:
            # Restore stdout and stderr
            sys.stdout, sys.stderr = original_stdout, original_stderr