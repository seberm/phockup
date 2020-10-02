import os
import re
from datetime import datetime


class Date:
    def __init__(self, filename=None):
        self.filename = filename

    def parse(self, date):
        replacements = [
            #("mm", "%M",),    # 35 (minute)
            #("YYYY", "%Y",),  # 2017 (year)
            #("YY", "%y",),    # 17 (year)
            #("m", "%b",),     # Dec (month)
            #("MM", "%m",),    # 12 (month)
            #("M", "%B",),     # December (month)
            #("DDD", "%j",),   # 123 (day or year)
            #("DD", "%d",),    # 25 (day)
            #("HH", "%H",),    # 08 (hour)
            #("ss", "%S",),    # 56 (second)

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
        return datetime(date_object["year"], date_object["month"], date_object["day"],
                        date_object["hour"] if date_object.get("hour") else 0,
                        date_object["minute"] if date_object.get("minute") else 0,
                        date_object["second"] if date_object.get("second") else 0)

    def from_exif(self, exif, timestamp=None, user_regex=None, date_field=None):
        if date_field:
            keys = date_field.split()
        else:
            keys = ['SubSecCreateDate', 'SubSecDateTimeOriginal', 'CreateDate', 'DateTimeOriginal']

        datestr = None

        for key in keys:
            if key in exif:
                datestr = exif[key]
                break

        # sometimes exif data can return all zeros
        # check to see if valid date first
        # sometimes this returns an int
        if datestr and isinstance(datestr, str) and not datestr.startswith('0000'):
            parsed_date = self.from_datestring(datestr)
        else:
            parsed_date = {
                'date': None,
                'subseconds': '',
            }

        if parsed_date.get("date") is not None:
            return parsed_date
        else:
            if self.filename:
                return self.from_filename(user_regex, timestamp)
            else:
                return parsed_date

    def from_datestring(self, datestr):
        datestr = datestr.split('.')
        date = datestr[0]

        if len(datestr) > 1:
            subseconds = datestr[1]
        else:
            subseconds = ''

        search = r'(.*)([+-]\d{2}:\d{2})'

        if re.search(search, date):
            date = re.sub(search, r'\1', date)

        try:
            parsed_date_time = self.strptime(date, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            try:
                parsed_date_time = self.strptime(date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                parsed_date_time = None

        if re.search(search, subseconds):
            subseconds = re.sub(search, r'\1', subseconds)

        return {
            'date': parsed_date_time,
            'subseconds': subseconds
        }

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
                return {
                    'date': date,
                    'subseconds': ''
                }

        if timestamp:
            return self.from_timestamp()

        # FIXME
        return {
            'date': None,
            'subseconds': '',
        }

    def from_timestamp(self):
        date = datetime.fromtimestamp(os.path.getmtime(self.filename))
        return {
            'date': date,
            'subseconds': '',
        }
