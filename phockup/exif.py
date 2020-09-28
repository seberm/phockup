from subprocess import (
    check_output,
    CalledProcessError,
)
import json
import logging


log = logging.getLogger(__name__)


class Exif:
    def __init__(self, filename):
        self.filename = filename

    @property
    def metadata(self):
        try:
            exif_command = [
                "exiftool",
                "-time:all",
                "-mimetype",
                "-json",
                self.filename,
            ]

            # TODO: Test if this code is still necessary on win platform
            #if sys.platform == 'win32':
            #    exif_command = exif_command.replace("\'", "\"")

            log.debug("Calling exiftool: %s", exif_command)
            output = check_output(exif_command).decode('UTF-8')

            # The exiftool output is a *list*, that's why we pop the first (the only) item.
            exif = json.loads(output).pop()
            log.debug("Got EXIF data for: %s => %s", self.filename, exif)
        except (CalledProcessError, UnicodeDecodeError) as e:
            log.debug(e)
            log.warning("It was not possible to retrieve EXIF data from file: %s", self.filename)
            return {}

        return exif
