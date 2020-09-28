import shutil
import logging

from phockup import PhockupError


log = logging.getLogger(__name__)


def check_dependencies():
    if shutil.which('exiftool') is None:
        raise PhockupError("Exiftool is not installed. Please install it using your package manager (probably package called perl-image-exiftool) or install it directly (Windows) from this website: http://www.sno.phy.queensu.ca/~phil/exiftool/")
