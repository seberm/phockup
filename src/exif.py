from subprocess import check_output, CalledProcessError
import json
import shlex
import sys


class Exif:
    def __init__(self, filename):
        self.filename = filename

    def data(self):
        try:
            exif_command = 'exiftool -time:all -mimetype -j %s' % shlex.quote(self.filename)
            if sys.platform == 'win32':
                exif_command = exif_command.replace("\'", "\"")
            data = check_output(exif_command, shell=True).decode('UTF-8')
            exif = json.loads(data)[0]
        except (CalledProcessError, UnicodeDecodeError):
            return None

        return exif
