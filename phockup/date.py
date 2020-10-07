import os
import sys
import re
import logging
from datetime import datetime

from dateutil.parser import parse


log = logging.getLogger(__name__)


class Date:
    def __init__(self, filename=None):
        self.filename = filename

    def parse(self, date):
        replacements = [
            # Keep following seperator replacements due to win/linux platform compatibility
            ("\\", os.path.sep,),  # path separator
            ("/", os.path.sep,),   # path separator
        ]

        for input_format, fmt_string in replacements:
            date = date.replace(input_format, fmt_string)

        return date

    def strptime(self, date, date_format):
        return datetime.strptime(date, date_format)

    def build(self, date_object):
        return datetime(
            year=date_object["year"],
            month=date_object["month"],
            day=date_object["day"],
            hour=date_object.get("hour", 0),
            minute=date_object.get("minute", 0),
            second=date_object.get("second", 0),
            microsecond=date_object.get("microsecond", 0),
        )

    def from_exif(self, exif, timestamp=None, user_regex=None, date_field=None):
        # FIXME: get default date_field from argparse?
        if date_field:
            keys = date_field.split()
        else:
            # Priority list
            keys = ['SubSecCreateDate', 'SubSecDateTimeOriginal', 'CreateDate', 'DateTimeOriginal']

        datestr = None

        for key in keys:
            if key in exif:
                datestr = exif[key]
                break

        parsed_date = None

        # sometimes exif data can return all zeros
        # check to see if valid date first
        # sometimes this returns an int
        if datestr and isinstance(datestr, str) and not datestr.startswith('0000'):
            parsed_date = self.from_datestring(datestr)

        if parsed_date:
            return parsed_date

        if self.filename:
            return self.from_filename(user_regex, timestamp)

        return parsed_date

    def from_datestring(self, datestr):
        """
        The standard EXIF date/time format is "YYYY:mm:dd HH:MM:SS", and some meta information formats such as XMP also allow sub-seconds and a timezone to be specified. The timezone format is
        "+HH:MM", "-HH:MM" or "Z".

        For example:
            exiftool -xmp:dateTimeOriginal="2005:10:23 20:06:34.33-05:00" a.jpg

        That's why we need to support multiple date/time formats.

        Ref.: https://exiftool.org/faq.html
        """
        log.debug("Trying to parse date/time string: %s", datestr)

        formats = [
            "%Y:%m:%d %H:%M:%S",
            "%Y:%m:%d %H:%M:%S.%f",

            "%Y:%m:%d %H:%M:%S.%f%z",

            # Possibly not needed, because the dateutil will handle it correctly
            "%Y-%m-%d %H:%M:%S",
        ]

        datetime_obj = None
        for strftime_format in formats:
            # Special handling of timezones to also support python v3.6. We must remove ':' from timezone (%z).
            # Note: The python version check is not needed, we can strip the colon for all pythons.
            #
            # Ref.: https://stackoverflow.com/questions/57995998/timezone-offset-in-datetime-format-in-python-3-6
            if f"{sys.version_info.major}.{sys.version_info.minor}" == "3.6":
                reg = r"[+-]\d{2}(:)\d{2}$"
                if re.match(reg, datestr):
                    log.debug("Python v3.6 workaround: stripping colon from timezone information for: %s", datestr)
                    datestr = re.sub(reg, r"\1", datestr)

            try:
                datetime_obj = datetime.strptime(datestr, strftime_format)
                break
            except ValueError as e:
                log.debug(e)
                log.debug("Failed to parse date/time string (tested format: %s): %s", strftime_format, datestr)
                continue
        else:
            log.debug("All date/time formats were tested, trying dateutil")
            try:
                datetime_obj = parse(datestr)
            except ValueError as e:
                log.debug(e)
                log.debug("Failed to parse date/time using dateutil")
                datetime_obj = None

        log.debug("Parsed date/time: %s", datetime_obj)
        return datetime_obj

    def from_filename(self, user_regex, timestamp=None):
        # If missing datetime from EXIF data check if filename is in datetime format.
        # For this use a user provided regex if possible.
        # Otherwise assume a filename such as IMG_20160915_123456.jpg as default.
        default_regex = re.compile(r'.*[_-](?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})[_-]?(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})')
        regex = user_regex or default_regex
        matches = regex.search(os.path.basename(self.filename))

        if matches:
            try:
                match_dir = matches.groupdict(default='0')
                match_dir = dict([a, int(x)] for a, x in match_dir.items())  # Convert str to int
                date = self.build(match_dir)
            except (KeyError, ValueError):
                date = None

            if date:
                return date

        if timestamp:
            return self.from_timestamp()

        return None

    def from_timestamp(self):
        return datetime.fromtimestamp(os.path.getmtime(self.filename))
