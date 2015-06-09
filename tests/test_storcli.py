#!/usr/bin/env python
__author__ = "Timothy McFadden"
__date__ = "06/03/2015"
__copyright__ = "Timothy McFadden, 2015"
__license__ = "MIT"
"""
This is a unit test for storcli-check.py
"""
import os
import sys
import logging
import unittest

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(THIS_DIR, "data")

sys.path.insert(0, os.path.abspath(os.path.join(THIS_DIR, '..', 'src')))
import storcli_check


def get_data_file_text(filename):
    single_file = os.path.join(DATA_DIR, filename)
    fh = open(single_file, "rb")
    text = fh.read()
    fh.close()
    return text


class TestMain(unittest.TestCase):
    def setUp(self):
        self.logger = storcli_check.get_logger()
        self.logger.setLevel(logging.CRITICAL)

    def test_single(self):
        path = os.path.join(DATA_DIR, "single-controller-ok")
        s = storcli_check.StorCLI(None, self.logger, _debug_dir=path)
        result, errors = s.ok()

        self.assertTrue(result)
        self.assertTrue(len(errors) == 0)

    def test_mutliple_offline(self):
        path = os.path.join(DATA_DIR, "multi-controller-offline")
        s = storcli_check.StorCLI(None, self.logger, _debug_dir=path)
        result, errors = s.ok()

        self.assertFalse(result)
        self.assertTrue(len(errors) > 0)
        self.assertTrue(len(s._controllers) == 3)

    def test_command(self):
        path = os.path.join(DATA_DIR, "single-controller-ok")
        s = storcli_check.StorCLI("python", self.logger, _debug_dir=path)
        result = s._command('-c "print \'Hello, World!\'"')
        self.assertTrue(result == "Hello, World!")

    def test_report_as_html_pass(self):
        path = os.path.join(DATA_DIR, "single-controller-ok")
        s = storcli_check.StorCLI("python", self.logger, _debug_dir=path)
        subject, body = s.report_as_html()

        self.assertTrue("Check Result: PASS" in subject)
        for substring in [
            "<b>PD Status</b>", "24:15&nbsp;&nbsp;&nbsp;&nbsp;15&nbsp;Onln",
            "1/1&nbsp;&nbsp;&nbsp;RAID10&nbsp;Optl", "Firmware Package:"
        ]:
            self.assertTrue(substring in body)

    def test_report_as_html_fail(self):
        path = os.path.join(DATA_DIR, "single-controller-offline")
        s = storcli_check.StorCLI("python", self.logger, _debug_dir=path)
        subject, body = s.report_as_html()

        self.assertTrue("Check Result: FAIL" in subject)


if __name__ == '__main__':
    unittest.main()
