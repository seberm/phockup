import argparse
import os
import re
import logging

from phockup.date import Date
from phockup.dependency import check_dependencies
from phockup.phockup import Phockup

from phockup import PhockupError


__version__ = "1.5.11"


log = logging.getLogger(__name__)


DEFAULT_LOGGING_MODE = "WARNING"

PROGRAM_DESCRIPTION = """Media sorting tool to organize photos and videos from your camera in folders by year, month and day.
The software will collect all files from the input and copy them to the output directory without
changing the file content. It will only rename the files and place them in the proper directory for year, month and day.
"""


PROGRAM_EPILOG = """
--------------------------------------------------------------------------------
Examle usage:
--------------------------------------------------------------------------------
$ phockup ~/Pictures/camera ~/Pictures/sorted
$ phockup ~/Pictures/*.jpg ~/Videos/vacation ~/photo.jpg ~/Pictures/sorted
$ phockup --dry-run --exclude '*.mp4' input-dir/ output-dir/
"""

DEFAULT_DIR_FORMAT = ['%Y', '%m', '%d']
DEFAULT_DIR_NAME = "unknown"
DEFAULT_IGNORED_FILES = [
    # Default windows files
    r"\.DS_Store",
    r"Thumbs\.db",
]


class CustomArgparseFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter,
):
    pass


def main():
    check_dependencies()

    parser = argparse.ArgumentParser(
        description=PROGRAM_DESCRIPTION,
        epilog=PROGRAM_EPILOG,
        allow_abbrev=False,
        formatter_class=CustomArgparseFormatter,
    )
    parser.version = "v%s" % __version__

    parser.add_argument(
        "-v",
        "--version",
        action="version",
    )

    parser.add_argument(
        "--log",
        action="store",
        type=str.upper,
        help="Logging level.",
        choices=["DEBUG", "WARNING", "INFO", "ERROR", "EXCEPTION"],
        default=DEFAULT_LOGGING_MODE,
    )

    parser.add_argument(
        "-d",
        "--date",
        action="store",
        type=Date().parse,
        help="""Specify date format for OUTPUTDIR directories.
You can choose different year format (e.g. 17 instead of 2017) or decide to
skip the day directories and have all photos sorted in year/month.

Supported formats:
    YYYY - 2016, 2017 ...
    YY   - 16, 17 ...
    MM   - 07, 08, 09 ...
    M    - July, August, September ...
    m    - Jul, Aug, Sept ...
    DD   - 27, 28, 29 ... (day of month)
    DDD  - 123, 158, 365 ... (day of year)

Example:
    YYYY/MM/DD -> 2011/07/17
    YYYY/M/DD  -> 2011/July/17
    YYYY/m/DD  -> 2011/Jul/17
    YY/m-DD    -> 11/Jul-17
        """,
    )

    exclusive_group = parser.add_mutually_exclusive_group()

    exclusive_group.add_argument(
        "-m",
        "--move",
        action="store_true",
        help="""Instead of copying the process will move all files from the input to the OUTPUTDIR.
This is useful when working with a big collection of files and the
remaining free space is not enough to make a copy of the input.
        """,
    )

    exclusive_group.add_argument(
        "-l",
        "--link",
        action="store_true",
        help="""Instead of copying the process will make hard links to all input files and place them in the OUTPUTDIR.
This is useful when working with working structure and want to create YYYY/MM/DD structure to point to the *same* files.
        """,
    )

    parser.add_argument(
        "-o",
        "--original-names",
        action="store_true",
        help="Organize the files in selected format or using the default year/month/day format but keep the original filenames.",
    )

    parser.add_argument(
        "-t",
        "--timestamp",
        action="store_true",
        help="""Use the timestamp of the file (last modified date) if there is no EXIF date information.
If the user supplies a regex, it will be used if it finds a match in the filename.
This option is intended as "last resort" since the file modified date may not be accurate,
nevertheless it can be useful if no other date information can be obtained.
        """,
    )

    parser.add_argument(
        "-y",
        "--dry-run",
        action="store_true",
        help="Don't move any files, just show which changes would be done.",
    )

    parser.add_argument(
        "-r",
        "--regex",
        action="store",
        type=re.compile,
        help="""Specify date format for date extraction from filenames if there is no EXIF date information.

Example:
    {regex}
    can be used to extract the date from file names like the following IMG_27.01.2015-19.20.00.jpg.
        """,
    )

    parser.add_argument(
        "--default-dir-name",
        action="store",
        help="The default directory name where are moved all files without datetime information.",
        default=DEFAULT_DIR_NAME,
    )

    parser.add_argument(
        "--exclude-regex",
        action="append",
        type=str,
        help="Exclude all files where their filename matches specified regex (e.g. 'image-[0-9]{2}\\.jpg').",
        default=DEFAULT_IGNORED_FILES,
    )

    parser.add_argument(
        "--exclude",
        action="append",
        type=str,
        help="Exclude all files where their filename matches an UNIX pattern (e.g. '*.txt'). The comparison is case-sensitive.",
        default=DEFAULT_IGNORED_FILES,
    )

    parser.add_argument(
        "--exclude-file",
        action="store",
        help="Specify exlusion file with list of UNIX patterns. All input files which match any of these patters will be ignored. One file pattern per line.",
    )

    parser.add_argument(
        "-f",
        "--date-field",
        action="store",
        type=re.compile,
        help="""Use a custom date extracted from the exif field specified.
To set multiple fields to try in order until finding a valid date,
use spaces to separate fields inside a string.

Example:
    DateTimeOriginal
    "DateTimeOriginal CreateDate FileModifyDate"

These fields are checked by default when this argument is not set:
    "SubSecCreateDate SubSecDateTimeOriginal CreateDate DateTimeOriginal"

To get all date fields available for a file, do:
    exiftool -time:all -mimetype -j <file>
        """,
    )

    parser.add_argument(
        "input_files",
        action="store",
        nargs="+",
        metavar="INPUTFILE",
        help="Specify the input file(s) or directory(ies) where your photos or videos are located.",
    )
    parser.add_argument(
        "output_dir",
        metavar="OUTPUTDIR",
        help="Specify the output directory where your photos and videos should be exported.",
    )

    args = parser.parse_args()

    # Setup the logging
    logging.basicConfig(level=args.log)

    if args.dry_run:
        log.warning("DRY-RUN: Dry-run mode active! Not making any changes.")

    pho = Phockup(
        args.input_files,
        args.output_dir,
        dir_format=os.path.sep.join(DEFAULT_DIR_FORMAT),
        move=args.move,
        link=args.link,
        date_regex=args.regex,
        original_filenames=args.original_names,
        timestamp=args.timestamp,
        date_field=args.date_field,
        dry_run=args.dry_run,
        default_dir_name=args.default_dir_name,

        exclude_regex=args.exclude_regex,
        exclude_unix=args.exclude,
        exclude_file=args.exclude_file,
    )

    try:
        pho.process()
    except PhockupError as e:
        log.error(e)
        return 99

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log.warning("Exiting...")
