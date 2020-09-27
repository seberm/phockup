#!/usr/bin/env python3
import sys

from phockup.__main__ import main
from phockup.printer import Printer

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        Printer().empty().line('Exiting...')
        sys.exit(0)
