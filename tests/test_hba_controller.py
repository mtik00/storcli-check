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


def get_data_file_text(info, events=None):
    event_text = ""
    info_text = ""

    single_file = os.path.join(DATA_DIR, info)
    fh = open(single_file, "rb")
    info_text = fh.read()
    fh.close()

    if events:
        single_file = os.path.join(DATA_DIR, events)
        fh = open(single_file, "rb")
        event_text = fh.read()
        fh.close()

    return (info_text, event_text)


class TestMain(unittest.TestCase):
    def setUp(self):
        self.logger = storcli_check.get_logger()
        self.logger.setLevel(logging.CRITICAL)

    def test_1(self):
        (info, events) = get_data_file_text("single-controller-hba.txt")

        c = storcli_check.Controller(info, events, self.logger)
        result, errors = c.ok()
        self.assertTrue(result)
        self.assertTrue(len(errors) == 0)
        self.assertTrue("Controller" in repr(c))
        self.assertTrue(len(c._vd_info) == 0)
        self.assertTrue(len(c._pd_info) == 0)

    def test_2(self):
        (info, events) = get_data_file_text("single-controller-hba-wrighrc.txt")

        c = storcli_check.Controller(info, events, self.logger)
        result, errors = c.ok()
        self.assertTrue(result)
        self.assertTrue(len(errors) == 0)
        self.assertTrue("Controller" in repr(c))
        self.assertTrue(len(c._vd_info) == 0)
        self.assertTrue(len(c._pd_info) == 0)


if __name__ == '__main__':
    unittest.main()
