import hashlib
import os
import re
import fnmatch
import shutil
import errno
import logging

from phockup import PhockupError
from phockup.date import Date
from phockup.exif import Exif


log = logging.getLogger(__name__)


class Phockup:

    @classmethod
    def is_image_or_video(self, mimetype):
        """
        Use mimetype to determine if the file is an image or video
        """
        log.debug("Checking MIME type. Current MIME type: %s", mimetype)
        pattern = re.compile('^(image/.+|video/.+|application/vnd.adobe.photoshop)$')
        if pattern.match(mimetype):
            return True

        return False

    def __init__(self, output_dir, **args):
        output_dir = os.path.expanduser(output_dir)

        self.output_dir = output_dir
        self.dir_format = args.get('dir_format', os.path.sep.join(['%Y', '%m', '%d']))
        self.move = args.get('move', False)
        self.link = args.get('link', False)
        self.date_regex = args.get('date_regex', None)
        self.timestamp = args.get('timestamp', False)
        self.date_field = args.get('date_field', False)
        self.dry_run = args.get('dry_run', False)
        self.default_dir_name = args.get('default_dir_name', 'unknown')
        self.exclude_regex = args.get('exclude_regex', [])
        self.exclude_unix = args.get('exclude_unix', [])
        self.exclude_file = args.get('exclude_file', None)
        self.rename = args.get('rename', False)

    def __call__(self):
        return self.process()

    def dry(self, fnc, *args, **kwargs):
        if self.dry_run:
            log.debug("Dry-run: Not calling function: %s(%s, %s)", fnc.__name__, args, kwargs)
            return

        fnc(*args, **kwargs)

    def process(self, input_files):
        """
        Check input data and ensure the output directory. After that
        start the processing of input files (and directories) one by one.
        """
        # Expand all input files
        i_files = [os.path.expanduser(i_file) for i_file in input_files]

        self.check_directories(i_files, self.output_dir)

        for i_file in i_files:
            if os.path.isdir(i_file):
                self.walk_directory(i_file)
            elif os.path.isfile(i_file):
                self.process_file(i_file)
            else:
                log.warning("Input file '%s' is not regular file or directory, continuing ...", i_file)
                continue

    def check_directories(self, input_files, output_dir):
        """
        Check if all input files/dirs and output directories exist.
        If output does not exists it tries to create it or it exits with an error.
        """
        log.debug("Checking input files and directories")
        if not input_files:
            raise PhockupError("No Input files or directories were provided.")

        # Create the output_dir when there is at least *one* valid file or directory
        # on the input
        at_least_one_valid_file = False

        for i_file in input_files:
            if not os.path.exists(i_file):
                log.warning("Input file/directory does not exist or cannot be accessed: %s, continuing ...", i_file)
                continue

            at_least_one_valid_file = True

        if not at_least_one_valid_file:
            raise PhockupError("There was no valid file on the input, exiting.")

        log.debug("Ensuring output directory: %s", output_dir)
        if at_least_one_valid_file:
            try:
                self.dry(os.makedirs, output_dir)
                log.info("Output directory was created: %s", output_dir)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    log.info("Output directory already exist: %s. Using existing directory.", output_dir)
                else:
                    log.error(e)
                    raise PhockupError("There was an error when creating directory: %s" % output_dir)

    def walk_directory(self, i_directory):
        """
        Walk given directory recursively and call process_file for each file except the ignored ones
        """
        for root, _, files in os.walk(i_directory):
            files.sort()
            for filename in files:

                # Regex file exclusion support
                if any(re.match(regex, filename) for regex in self.exclude_regex):
                    log.debug("The file %s matched exclusion regex, excluding ...", filename)
                    continue

                # UNIX pattern file exclusion (case-sensitive)
                # Ref.: https://docs.python.org/3/library/fnmatch.html
                if any(fnmatch.fnmatchcase(filename, pattern) for pattern in self.exclude_unix):
                    log.debug("The file %s matched exclusion UNIX pattern, excluding ...", filename)
                    continue

                if self.exclude_file:
                    with open(self.exclude_file) as fd:
                        ignore_file = False

                        for pattern in fd:
                            # Strip the '\n' from the end of file
                            # FIXME: What about other platforms (win)
                            if fnmatch.fnmatchcase(filename, pattern[:-1]):
                                log.debug("The file %s matched UNIX pattern (%s) in exclusion file (%s), excluding ...", filename, pattern[:-1], self.exclude_file)
                                ignore_file = True
                                break

                        if ignore_file:
                            continue

                filepath = os.path.join(root, filename)
                self.process_file(filepath)

    def checksum(self, filename):
        """
        Calculate checksum for a file.
        Used to match if duplicated file name is actually a duplicated file
        """
        block_size = 65536
        sha256 = hashlib.sha256()
        with open(filename, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                sha256.update(block)
        return sha256.hexdigest()

    def get_output_dir(self, date=None):
        """
        Generate output directory path based on the extracted date and formatted
        using dir_format. If date is None (probably missing from the EXIF data)
        the file is going to directory specified by default-dir-name option,
        unless user included a regex from filename or uses timestamp.
        """
        path = [self.output_dir, self.default_dir_name]
        if date:
            path = [self.output_dir, date.date().strftime(self.dir_format)]

        fullpath = os.path.sep.join(path)

        try:
            self.dry(os.makedirs, fullpath)
        except OSError as e:
            if e.errno == errno.EEXIST:
                log.debug("Child directory already exist: %s. Using existing directory.", fullpath)
            else:
                log.error(e)
                raise PhockupError("There was an error when creating directory: %s" % fullpath)

        return fullpath

    def get_file_name(self, original_filename, date=None):
        """
        Generate file name based on exif data unless it is missing or
        original filenames are required. Then use original file name.
        """
        if not self.rename:
            return os.path.basename(original_filename)

        if not date and date.get("date") is None:
            log.debug("Filename was not possible to determine from EXIF, returning original name.")
            return os.path.basename(original_filename)

        log.debug("Trying to rename the input file based on EXIF data: %s", original_filename)

        new_filename = date["date"].strftime(self.rename)

        #filename = [
        #    '%04d' % date['date'].year,
        #    '%02d' % date['date'].month,
        #    '%02d' % date['date'].day,
        #    '-',
        #    '%02d' % date['date'].hour,
        #    '%02d' % date['date'].minute,
        #    '%02d' % date['date'].second,
        #]

        # FIXME: improve support of subseconds
        if date['subseconds']:
            new_filename += (date['subseconds'])

        # Append the file extension
        new_filename += os.path.splitext(original_filename)[1]

        log.debug("Determined new filename for %s => %s", original_filename, new_filename)
        return new_filename

    def process_file(self, filename):
        """
        Process the file using the selected strategy
        If file is .xmp skip it so process_xmp method can handle it
        """
        log.debug("Processing file: %s", filename)
        if str.endswith(filename, '.xmp'):
            log.debug("Current file is '.xmp' file and it is going to be handled separately: %s", filename)
            return None

        output, target_file_name, target_file_path = self.get_file_name_and_path(filename)

        suffix = 1
        target_file = target_file_path

        while True:
            if os.path.isfile(target_file):
                chcksum_filename = self.checksum(filename)
                chcksum_target_file = self.checksum(target_file)

                if chcksum_filename == chcksum_target_file:
                    log.warning('%s => skipped, duplicated file %s', filename, target_file)
                    log.debug('sha256(%s) == sha256(%s) == %s', filename, target_file, chcksum_filename)
                    break
            else:
                if self.move:
                    try:
                        self.dry(shutil.move, filename, target_file)
                    except FileNotFoundError:
                        log.warning('%s => skipped, no such file or directory', filename)
                        break
                elif self.link:
                    self.dry(os.link, filename, target_file)
                else:
                    try:
                        self.dry(shutil.copy2, filename, target_file)
                    except FileNotFoundError:
                        log.warning('%s => skipped, no such file or directory', filename)
                        break

                log.info('%s => %s', filename, target_file)
                self.process_xmp(filename, target_file_name, suffix, output)
                break

            suffix += 1
            target_split = os.path.splitext(target_file_path)
            target_file = "%s-%d%s" % (target_split[0], suffix, target_split[1])

    def get_file_name_and_path(self, filename):
        """
        Returns target file name and path
        """
        exif_data = Exif(filename).metadata

        if exif_data and 'MIMEType' in exif_data and self.is_image_or_video(exif_data['MIMEType']):
            date = Date(filename).from_exif(exif_data, self.timestamp, self.date_regex, self.date_field)
            output = self.get_output_dir(date["date"])
            target_file_name = self.get_file_name(filename, date)
            target_file_path = os.path.sep.join([output, target_file_name])
        else:
            log.info("No EXIF data found, getting datetime information from file modification.")
            output = self.get_output_dir()
            target_file_name = os.path.basename(filename)
            target_file_path = os.path.sep.join([output, target_file_name])

        return output, target_file_name, target_file_path

    def process_xmp(self, original_filename, target_file_name, suffix, output):
        """
        Process xmp files. These are meta data for RAW images
        """
        log.debug("XMP: processing all '.xmp' files for: %s", original_filename)
        xmp_original_with_ext = original_filename + '.xmp'
        xmp_original_without_ext = os.path.splitext(original_filename)[0] + '.xmp'

        suffix = '-%s' % suffix if suffix > 1 else ''

        xmp_files = {}

        if os.path.isfile(xmp_original_with_ext):
            xmp_target = '%s%s.xmp' % (target_file_name, suffix)
            xmp_files[xmp_original_with_ext] = xmp_target
        if os.path.isfile(xmp_original_without_ext):
            xmp_target = '%s%s.xmp' % (os.path.splitext(target_file_name)[0], suffix)
            xmp_files[xmp_original_without_ext] = xmp_target

        for original, target in xmp_files.items():
            xmp_path = os.path.sep.join([output, target])
            log.info("%s => %s", original, xmp_path)

            if self.move:
                self.dry(shutil.move, original, xmp_path)
            elif self.link:
                self.dry(os.link, original, xmp_path)
            else:
                self.dry(shutil.copy2, original, xmp_path)
