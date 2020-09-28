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
    def __init__(self, input_files, output_dir, **args):
        # Expand all input files
        # FIXME: remove input_files argument, add it into self.process(input_files) - improve the API
        input_files = [os.path.expanduser(i_file) for i_file in input_files]
        output_dir = os.path.expanduser(output_dir)

        self.input_files = input_files
        self.output_dir = output_dir
        self.dir_format = args.get('dir_format', os.path.sep.join(['%Y', '%m', '%d']))
        self.move = args.get('move', False)
        self.link = args.get('link', False)
        self.original_filenames = args.get('original_filenames', False)
        self.date_regex = args.get('date_regex', None)
        self.timestamp = args.get('timestamp', False)
        self.date_field = args.get('date_field', False)
        self.dry_run = args.get('dry_run', False)
        self.default_dir_name = args.get('default_dir_name', 'unknown')
        self.exclude_regex = args.get('exclude_regex', [])
        self.exclude_unix = args.get('exclude_unix', [])
        self.exclude_file = args.get('exclude_file', None)

    def __call__(self):
        return self.process()

    def process(self):
        """
        Check input data and ensure the output directory. After that
        start the processing of input files (and directories) one by one.
        """
        self.check_directories()

        for i_file in self.input_files:
            if os.path.isdir(i_file):
                self.walk_directory(i_file)
            elif os.path.isfile(i_file):
                self.process_file(i_file)
            else:
                log.warning("Input file '%s' is not regular file or directory, continuing ...", i_file)
                continue

    def check_directories(self):
        """
        Check if all input files/dirs and output directories exist.
        If output does not exists it tries to create it or it exits with an error.
        """
        log.debug("Checking input files and directories")
        if not self.input_files:
            raise PhockupError("No Input files or directories were provided.")

        # Create the output_dir when there is at least *one* valid file or directory
        # on the input
        at_least_one_valid_file = False

        for i_file in self.input_files:
            if not os.path.exists(i_file):
                log.warning("Input file does not exist or cannot be accessed: %s, continuing ...", i_file)
                continue

            at_least_one_valid_file = True

        if not at_least_one_valid_file:
            raise PhockupError("There was no valid file on the input, exiting.")

        log.debug("Ensuring output directory: %s", self.output_dir)
#        if not os.path.exists(self.output_dir) and at_least_one_valid_file:
        if at_least_one_valid_file:
            try:
                if not self.dry_run:
                    os.makedirs(self.output_dir)
                    log.info("Output directory was created: %s", self.output_dir)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    log.info("Output directory already exist: %s. Using existing directory.", self.output_dir)
                else:
                    log.error(e)
                    raise PhockupError("There was an error when creating directory: %s" % self.output_dir)

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

    def is_image_or_video(self, mimetype):
        """
        Use mimetype to determine if the file is an image or video
        """
        log.debug("Checking MIME type. Current MIME type: %s", mimetype)
        pattern = re.compile('^(image/.+|video/.+|application/vnd.adobe.photoshop)$')
        if pattern.match(mimetype):
            return True

        return False

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
            if not self.dry_run:
                os.makedirs(fullpath)
        except OSError as e:
            if e.errno == errno.EEXIST:
                log.debug("Child directory already exist: %s. Using existing directory.", fullpath)
            else:
                log.error(e)
                raise PhockupError("There was an error when creating directory: %s" % fullpath)

        return fullpath

    def get_file_name(self, original_filename, date):
        """
        Generate file name based on exif data unless it is missing or
        original filenames are required. Then use original file name.
        """
        log.debug("Determining new filename for: %s", original_filename)

        if self.original_filenames:
            log.debug("Original filenames flag active, returning original name.")
            return os.path.basename(original_filename)

        filename = [
            '%04d' % date['date'].year,
            '%02d' % date['date'].month,
            '%02d' % date['date'].day,
            '-',
            '%02d' % date['date'].hour,
            '%02d' % date['date'].minute,
            '%02d' % date['date'].second,
        ]

        if date['subseconds']:
            filename.append(date['subseconds'])

        new_filename = ''.join(filename) + os.path.splitext(original_filename)[1]
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
                if self.checksum(filename) == self.checksum(target_file):
                    log.warning('%s => skipped, duplicated file %s', filename, target_file)
                    break
            else:
                if self.move:
                    try:
                        if not self.dry_run:
                            shutil.move(filename, target_file)
                    except FileNotFoundError:
                        log.warning('%s => skipped, no such file or directory', filename)
                        break
                elif self.link and not self.dry_run:
                    os.link(filename, target_file)
                else:
                    try:
                        if not self.dry_run:
                            shutil.copy2(filename, target_file)
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
            if not self.original_filenames:
                target_file_name = target_file_name.lower()
            target_file_path = os.path.sep.join([output, target_file_name])
        else:
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

            if not self.dry_run:
                if self.move:
                    shutil.move(original, xmp_path)
                elif self.link:
                    os.link(original, xmp_path)
                else:
                    shutil.copy2(original, xmp_path)
