import shutil
import os
import errno
from datetime import datetime

import pytest

from phockup.dependency import check_dependencies
from phockup.phockup import Phockup
# from phockup.exif import Exif
from phockup import PhockupError


os.chdir(os.path.dirname(__file__))


def test_check_dependencies(mocker):
    mocker.patch('shutil.which', return_value='exiftool')

    check_dependencies()


def test_check_dependencies_missing(mocker):
    mocker.patch('shutil.which', return_value=None)

    with pytest.raises(PhockupError):
        check_dependencies()


def test_exit_if_missing_input_directory(mocker):
    mocker.patch('os.makedirs')
    mocker.patch('sys.exit')

    with pytest.raises(PhockupError, match=r"There was no valid file on the input, exiting\."):
        Phockup('out').process(['in'])


# #def test_removing_trailing_slash_for_input_output(mocker):
# #    mocker.patch('os.makedirs')
# #    mocker.patch('sys.exit')
# #    phockup = Phockup(['in/'], 'out/').process()
# #    assert phockup.input_dir == 'in'
# #    assert phockup.output_dir == 'out'


def test_error_for_missing_input_dir(mocker, capsys):
    with pytest.raises(PhockupError, match=r"No Input files or directories were provided\."):
        Phockup('out').process([])


def test_error_for_no_write_access_when_creating_output_dir(mocker, capsys):
    mocker.patch.object(Phockup, 'walk_directory')
    mocker.patch.object(Phockup, 'process_file')
    mocker.patch('os.makedirs', side_effect=OSError(errno.EACCES))

    with pytest.raises(PhockupError, match=r"There was an error when creating directory"):
        Phockup(os.path.join('%sroot' % os.path.sep, 'phockup')).process(['input'])


def test_walking_directory():
    shutil.rmtree('output', ignore_errors=True)
    Phockup('output').process(['input'])

    dir1 = os.path.join('output', '2017', '01', '01')
    dir2 = os.path.join('output', '2017', '10', '06')
    dir3 = os.path.join('output', 'unknown')
    assert os.path.isdir(dir1)
    assert os.path.isdir(dir2)
    assert os.path.isdir(dir3)
    assert len([name for name in os.listdir(dir1) if os.path.isfile(os.path.join(dir1, name))]) == 3
    assert len([name for name in os.listdir(dir2) if os.path.isfile(os.path.join(dir2, name))]) == 1
    assert len([name for name in os.listdir(dir3) if os.path.isfile(os.path.join(dir3, name))]) == 1
    shutil.rmtree('output', ignore_errors=True)


def test_dry_run():
    shutil.rmtree('output', ignore_errors=True)
    Phockup('output', dry_run=True).process(['input'])

    assert not os.path.isdir('output')
    dir1 = os.path.join('output', '2017', '01', '01')
    dir2 = os.path.join('output', '2017', '10', '06')
    dir3 = os.path.join('output', 'unknown')
    assert not os.path.isdir(dir1)
    assert not os.path.isdir(dir2)
    assert not os.path.isdir(dir3)


def test_is_image_or_video(mocker):
    mocker.patch.object(Phockup, 'check_directories')

    assert Phockup.is_image_or_video("image/jpeg")
    assert Phockup.is_image_or_video("video/mp4")
    assert not Phockup.is_image_or_video("foo/bar")


def test_get_file_name(mocker):
    mocker.patch.object(Phockup, 'check_directories')
    mocker.patch.object(Phockup, 'walk_directory')

    date = {
        "date": datetime(2017, 1, 1, 1, 1, 1),
        "subseconds": "20",
    }

    assert Phockup('out').get_file_name(os.path.join("Bar", "Foo.jpg"), date) == "20170101-01010120.jpg"


def test_get_file_name_is_original_on_exception(mocker):
    mocker.patch.object(Phockup, 'check_directories')
    mocker.patch.object(Phockup, 'walk_directory')

    assert Phockup('out').get_file_name(os.path.join("Bar", "Foo.jpg"), {"date": None}) == "Foo.jpg"


# def test_process_file_with_filename_date(mocker):
#     shutil.rmtree('output', ignore_errors=True)
#     mocker.patch.object(Phockup, 'check_directories')
#     mocker.patch.object(Phockup, 'walk_directory')
#     mocker.patch.object(Exif, 'metadata')
#     Exif.metadata.return_value = {
#         "MIMEType": "image/jpeg"
#     }
#
#     Phockup('output').process_file("input/date_20170101_010101.jpg")
#     assert os.path.isfile("output/2017/01/01/20170101-010101.jpg")
#     shutil.rmtree('output', ignore_errors=True)


def test_process_link_to_file_with_filename_date(mocker):
    shutil.rmtree('output', ignore_errors=True)
    mocker.patch.object(Phockup, 'check_directories')
    mocker.patch.object(Phockup, 'walk_directory')

    Phockup('output').process_file(os.path.join("input", "link_to_date_20170101_010101.jpg"))
    assert os.path.isfile(os.path.join("output", "2017", "01", "01", "20170101-010101.jpg"))
    shutil.rmtree('output', ignore_errors=True)


# #def test_process_broken_link(mocker, capsys):
# #    shutil.rmtree('output', ignore_errors=True)
# #    mocker.patch.object(Phockup, 'check_directories')
# #    mocker.patch.object(Phockup, 'walk_directory')
# #    Phockup([], 'output').process_file(os.path.join("input", "not_a_file.jpg"))
# #    assert 'skipped, no such file or directory' in capsys.readouterr()[0]
# #    shutil.rmtree('output', ignore_errors=True)
#
#
# #def test_process_broken_link_move(mocker, capsys):
# #    shutil.rmtree('output', ignore_errors=True)
# #    mocker.patch.object(Phockup, 'check_directories')
# #    mocker.patch.object(Phockup, 'walk_directory')
# #    phockup = Phockup([], 'output', move=True)
# #    phockup.process_file(os.path.join("input", "not_a_file.jpg"))
# #    assert 'skipped, no such file or directory' in capsys.readouterr()[0]
# #    shutil.rmtree('output', ignore_errors=True)


def test_process_image_exif_date(mocker):
    shutil.rmtree('output', ignore_errors=True)
    mocker.patch.object(Phockup, 'check_directories')
    mocker.patch.object(Phockup, 'walk_directory')

    Phockup('output').process_file(os.path.join("input", "exif.jpg"))
    assert os.path.isfile(os.path.join("output", "2017", "01", "01", "20170101-010101.jpg"))
    shutil.rmtree('output', ignore_errors=True)


def test_process_image_xmp(mocker):
    shutil.rmtree('output', ignore_errors=True)
    mocker.patch.object(Phockup, 'check_directories')
    mocker.patch.object(Phockup, 'walk_directory')

    Phockup('output').process_file(os.path.join("input", "xmp.jpg"))
    assert os.path.isfile(os.path.join("output", "2017", "01", "01", "20170101-010101.jpg"))
    assert os.path.isfile(os.path.join("output", "2017", "01", "01", "20170101-010101.jpg.xmp"))
    shutil.rmtree('output', ignore_errors=True)


def test_process_image_xmp_noext(mocker):
    shutil.rmtree('output', ignore_errors=True)
    mocker.patch.object(Phockup, 'check_directories')
    mocker.patch.object(Phockup, 'walk_directory')

    Phockup('output').process_file(os.path.join("input", "xmp_noext.jpg"))
    assert os.path.isfile(os.path.join("output", "2017", "01", "01", "20170101-010101.jpg"))
    assert os.path.isfile(os.path.join("output", "2017", "01", "01", "20170101-010101.xmp"))
    shutil.rmtree('output', ignore_errors=True)


def test_process_image_xmp_ext_and_noext(mocker):
    shutil.rmtree('output', ignore_errors=True)
    mocker.patch.object(Phockup, 'check_directories')
    mocker.patch.object(Phockup, 'walk_directory')

    Phockup('output').process_file(os.path.join("input", "xmp_ext.jpg"))
    assert os.path.isfile(os.path.join("output", "2017", "01", "01", "20170101-010101.jpg"))
    assert os.path.isfile(os.path.join("output", "2017", "01", "01", "20170101-010101.xmp"))
    assert os.path.isfile(os.path.join("output", "2017", "01", "01", "20170101-010101.jpg.xmp"))
    shutil.rmtree('output', ignore_errors=True)


# def test_process_image_unknown(mocker):
#     shutil.rmtree('output', ignore_errors=True)
#     mocker.patch.object(Phockup, 'check_directories')
#     mocker.patch.object(Phockup, 'walk_directory')
#     mocker.patch.object(Exif, 'metadata')
#     Exif.metadata.return_value = {
#         "MIMEType": "image/jpeg"
#     }
#
#     Phockup('output').process_file(os.path.join("input", "UNKNOWN.jpg"))
#     assert os.path.isfile(os.path.join("output", "unknown", "unknown.jpg"))
#     shutil.rmtree('output', ignore_errors=True)


def test_process_other(mocker):
    shutil.rmtree('output', ignore_errors=True)
    mocker.patch.object(Phockup, 'check_directories')
    mocker.patch.object(Phockup, 'walk_directory')

    Phockup('output').process_file(os.path.join("input", "other.txt"))
    assert os.path.isfile(os.path.join("output", "unknown", "other.txt"))
    shutil.rmtree('output', ignore_errors=True)


#def test_process_move(mocker):
#    shutil.rmtree('output', ignore_errors=True)
#    mocker.patch.object(Phockup, 'check_directories')
#    mocker.patch.object(Phockup, 'walk_directory')
#    mocker.patch.object(Exif, 'metadata')
#    Exif.metadata.return_value = {
#        "MIMEType": "image/jpeg"
#    }
#
#    phockup = Phockup('output', move=True)
#    open(os.path.join("input", "tmp_20170101_010101.jpg"), "w").close()
#    open(os.path.join("input", "tmp_20170101_010101.xmp"), "w").close()
#    phockup.process_file(os.path.join("input", "tmp_20170101_010101.jpg"))
#    phockup.process_file(os.path.join("input", "tmp_20170101_010101.xmp"))
#    assert not os.path.isfile(os.path.join("input", "tmp_20170101_010101.jpg"))
#    assert not os.path.isfile(os.path.join("input", "tmp_20170101_010101.xmp"))
#    assert os.path.isfile("output", "2017", "01", "01", "20170101-010101.jpg"))
#    assert os.path.isfile("output", "2017", "01", "01", "20170101-010101.xmp"))
#    shutil.rmtree('output', ignore_errors=True)


# def test_process_link(mocker):
#     shutil.rmtree('output', ignore_errors=True)
#     mocker.patch.object(Phockup, 'check_directories')
#     mocker.patch.object(Phockup, 'walk_directory')
#     mocker.patch.object(Exif, 'data')
#     Exif.data.return_value = {
#         "MIMEType": "image/jpeg"
#     }
#     phockup = Phockup([], 'output', link=True)
#     open(os.path.join("input", "tmp_20170101_010101.jpg"), "w").close()
#     open(os.path.join("input", "tmp_20170101_010101.xmp"), "w").close()
#     phockup.process_file(os.path.join("input", "tmp_20170101_010101.jpg"))
#     phockup.process_file(os.path.join("input", "tmp_20170101_010101.xmp"))
#     assert os.path.isfile(os.path.join("input", "tmp_20170101_010101.jpg"))
#     assert os.path.isfile(os.path.join("input", "tmp_20170101_010101.xmp"))
#     assert os.path.isfile(os.path.join("output", "2017", "01", "01", "20170101-010101.jpg"))
#     assert os.path.isfile(os.path.join("output", "2017", "01", "01", "20170101-010101.xmp"))
#     shutil.rmtree('output', ignore_errors=True)
#     os.remove(os.path.join("input", "tmp_20170101_010101.jpg"))
#     os.remove(os.path.join("input", "tmp_20170101_010101.xmp"))

# #def test_process_exists_same(mocker, capsys):
# #    shutil.rmtree('output', ignore_errors=True)
# #    mocker.patch.object(Phockup, 'check_directories')
# #    mocker.patch.object(Phockup, 'walk_directory')
# #    phockup = Phockup([], 'output')
# #    phockup.process_file(os.path.join("input", "exif.jpg"))
# #    assert os.path.isfile(os.path.join("output", "2017", "01", "01", "20170101-010101.jpg"))
# #    phockup.process_file(os.path.join("input", "exif.jpg"))
# #    assert 'skipped, duplicated file' in capsys.readouterr()[0]
# #    shutil.rmtree('output', ignore_errors=True)


# def test_process_same_date_different_files_rename(mocker):
#     shutil.rmtree('output', ignore_errors=True)
#     mocker.patch.object(Phockup, 'check_directories')
#     mocker.patch.object(Phockup, 'walk_directory')
#     phockup = Phockup([], 'output')
#     phockup.process_file(os.path.join("input", "exif.jpg"))
#     mocker.patch.object(Exif, 'data')
#     Exif.data.return_value = {
#         "MIMEType": "image/jpeg",
#         "CreateDate": "2017:01:01 01:01:01"
#     }
#     phockup.process_file(os.path.join("input", "date_20170101_010101.jpg"))
#     assert os.path.isfile(os.path.join("output", "2017", "01", "01", "20170101-010101-2.jpg"))
#     shutil.rmtree('output', ignore_errors=True)

def test_process_skip_xmp(mocker):
    # Assume no errors == skip XMP file
    mocker.patch.object(Phockup, 'check_directories')
    mocker.patch.object(Phockup, 'walk_directory')
    phockup = Phockup('output')
    phockup.process_file("skip.xmp")


def test_process_skip_ignored_file():
    shutil.rmtree('output', ignore_errors=True)
    shutil.rmtree('input_ignored', ignore_errors=True)
    os.mkdir('input_ignored')
    open(os.path.join("input_ignored", ".DS_Store"), "w").close()
    Phockup('output', exclude_regex=[r'\.DS_Store']).process(['input_ignored'])
    assert not os.path.isfile(os.path.join("output", "unknown", ".DS_Store"))
    shutil.rmtree('output', ignore_errors=True)
    shutil.rmtree('input_ignored', ignore_errors=True)


def test_keep_original_filenames(mocker):
    shutil.rmtree('output', ignore_errors=True)
    mocker.patch.object(Phockup, 'check_directories')
    mocker.patch.object(Phockup, 'walk_directory')

    Phockup('output', original_filenames=True).process_file(os.path.join("input", "exif.jpg"))
    assert os.path.isfile(os.path.join("output", "2017", "01", "01", "exif.jpg"))
    assert not os.path.isfile(os.path.join("output", "2017", "01", "01", "20170101-010101.jpg"))
    shutil.rmtree('output', ignore_errors=True)


def test_keep_original_filenames_and_filenames_case(mocker):
    shutil.rmtree('output', ignore_errors=True)
    mocker.patch.object(Phockup, 'check_directories')
    mocker.patch.object(Phockup, 'walk_directory')

    Phockup('output', original_filenames=True).process_file(os.path.join("input", "UNKNOWN.jpg"))
    assert os.path.isfile(os.path.join("output", "2017", "10", "06", "UNKNOWN.jpg"))
    assert 'unknown.jpg' not in os.listdir(os.path.join("output", "2017", "10", "06"))
    shutil.rmtree('output', ignore_errors=True)
