#!/usr/bin/env python
__author__ = "Timothy McFadden"
__date__ = "06/02/2015"
__copyright__ = "Timothy McFadden, 2015"
__license__ = "MIT"
__version__ = "0.01"
"""
This is the unit test for storcli-check.py
"""
import os
import sys
import logging
import zipfile
import tempfile
import unittest

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(THIS_DIR, "data")

sys.path.insert(0, os.path.abspath(os.path.join(THIS_DIR, '..')))
import storcli_check


class TestMain(unittest.TestCase):
    def setUp(self):
        self.logger = storcli_check.get_logger()
        self.logger.setLevel(logging.CRITICAL)

    def test_find_storcli(self):

        if "win" in sys.platform:
            fh = open("storcli.exe", "wb")
            fh.close()
            self.assertTrue("storcli.exe" in storcli_check.find_storcli(self.logger))
            os.unlink("storcli.exe")

        self.assertRaises(Exception, storcli_check.find_storcli, self.logger, ["storcli-doesnt-exist"])
        self.assertTrue(storcli_check.find_storcli(self.logger))

    def test_get_logger(self):
        l = storcli_check.get_logger(logfile_path="tmplog.txt", logfile_mode="wb")
        l.debug("testing")
        logging.shutdown()

        self.assertTrue(os.path.exists("tmplog.txt"))
        os.unlink("tmplog.txt")

    def test_flush_logfile(self):
        storcli_check.get_logger(logfile_path="tmplog.txt", logfile_mode="wb")
        storcli_check.flush_logfile(self.logger)

    def test_remove_directory(self):
        newdir = tempfile.mkdtemp()
        subdir = os.path.join(newdir, "test-dir")
        os.makedirs(subdir)

        files = [os.path.join(x, "test.txt") for x in [newdir, subdir]]

        for file_ in files:
            fh = open(file_, "wb")
            fh.close()

        self.assertTrue(os.path.isdir(newdir))
        self.assertTrue(os.path.isdir(subdir))

        for file_ in files:
            self.assertTrue(os.path.isfile(file_))

        storcli_check.remove_directory(newdir)

        self.assertFalse(os.path.isdir(newdir))
        self.assertFalse(os.path.isdir(subdir))

        for file_ in files:
            self.assertFalse(os.path.isfile(file_))

    def test_zip(self):
        newdir = tempfile.mkdtemp()
        subdir = os.path.join(newdir, "test-dir")
        os.makedirs(subdir)

        files = [os.path.join(x, "test.txt") for x in [newdir, subdir]]

        for file_ in files:
            fh = open(file_, "wb")
            fh.close()

        zip_dest_dir = tempfile.mkdtemp()
        zip_dest = os.path.join(zip_dest_dir, "test.zip")

        fd, other_file = tempfile.mkstemp(dir=zip_dest_dir)
        os.close(fd)
        os.rename(other_file, other_file + "-test.txt")
        other_file += "-test.txt"

        storcli_check.zip([newdir, other_file], zip_dest)

        self.assertTrue(os.path.isfile(zip_dest))

        zf = zipfile.ZipFile(zip_dest, 'r')
        zipped_files = zf.infolist()
        zf.close()

        self.assertTrue(len(zipped_files) == 3)
        self.assertTrue(zipped_files[0].filename.endswith("test.txt"))
        self.assertTrue(zipped_files[1].filename.endswith("test.txt"))
        self.assertTrue(zipped_files[2].filename.endswith("test.txt"))

        storcli_check.remove_directory(newdir)
        storcli_check.remove_directory(zip_dest_dir)

    def test_sendmail(self):
        newdir = tempfile.mkdtemp()
        filename = os.path.join(newdir, "test.txt")
        fh = open(filename, "wb")
        fh.write("Hello, World!\n")
        fh.close()

        # This should raise an exception since the mailserver doesn't really exist
        self.assertRaises(
            Exception, storcli_check.sendmail,
            subject="test", to="nobody@example.com,nobody@example.com",
            sender="me@nowhere.com", body="<b>Hello, World!</b>",
            mailserver="mailhost@asdf123.net",
            attachments=[filename],
            cc="nobody@example.com,nobody@example.com")

        # Cover the case were cc is empty
        self.assertRaises(
            Exception, storcli_check.sendmail,
            subject="test", to="nobody@example.com,nobody@example.com",
            sender="me@nowhere.com", body="<b>Hello, World!</b>",
            mailserver="mailhost@asdf123.net",
            attachments=[filename],
            cc=None)
        storcli_check.remove_directory(newdir)

    def test_parse_arumgnents(self):
        parser_ = storcli_check.init_parser()

        self.assertRaises(SystemExit, storcli_check.parse_arguments, parser_, self.logger, [])

        args = ["--to", "test@example.com", "--mailserver", "mailhost.example.com"]
        (options, args) = storcli_check.parse_arguments(parser_, self.logger, args)
        self.assertTrue(len(args) == 0)
        self.assertTrue(options.mail_to == "test@example.com")
        self.assertTrue(options.mail_server == "mailhost.example.com")


if __name__ == '__main__':
    unittest.main()
