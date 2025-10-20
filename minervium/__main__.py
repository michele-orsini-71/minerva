"""
Entry point for running Minervium as a module: python -m minervium
"""

import sys
from minervium.cli import main

if __name__ == '__main__':
    sys.exit(main())
