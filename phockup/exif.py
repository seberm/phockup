from subprocess import (
    check_output,
    CalledProcessError,
)
import json
import shlex
import sys
import logging


log = logging.getLogger(__name__)


class Exif:
    def __init__(self, filename):
        self.filename = filename

    def data(self):
        try:
            exif_command = 'exiftool -time:all -mimetype -j %s' % shlex.quote(self.filename)
            if sys.platform == 'win32':
                exif_command = exif_command.replace("\'", "\"")

            log.debug("Calling exiftool: %s", exif_command)
            data = check_output(exif_command, shell=True).decode('UTF-8')
            exif = json.loads(data)[0]
            log.debug("Got EXIF data for: %s => %s", self.filename, exif)
        except (CalledProcessError, UnicodeDecodeError):
            return None

        return exif
