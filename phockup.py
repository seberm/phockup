#!/usr/bin/env python3

import sys
import logging

from phockup.__main__ import main


log = logging.getLogger(__name__)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        log.warning("Exiting...")
        sys.exit(0)
