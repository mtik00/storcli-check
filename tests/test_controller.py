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

    def test_clean(self):
        (info, events) = get_data_file_text("single-controller.txt")

        c = storcli_check.Controller(info, events, self.logger)
        result, errors = c.ok()
        self.assertTrue(result)
        self.assertTrue(len(errors) == 0)
        self.assertTrue("Controller" in repr(c))
        self.assertTrue(len(c._vd_info) == 2)
        self.assertTrue(len(c._pd_info) == 16)
        self.assertTrue(c._cv_info)
        self.assertFalse(c._event_info)

    def test_degraded(self):
        (info, events) = get_data_file_text("single-controller-degraded.txt")

        c = storcli_check.Controller(info, events, self.logger)
        result, errors = c.ok()

        self.assertFalse(result)
        self.assertTrue(len(errors) == 3)
        self.assertTrue([x for x in errors if "dgrd" in x])
        self.assertTrue([x for x in errors if "offln" in x])
        self.assertTrue([x for x in errors if "failure" in x])

        self.assertTrue("Controller" in repr(c))
        self.assertTrue(len(c._vd_info) == 2)
        self.assertTrue(len(c._pd_info) == 16)
        self.assertTrue(c._cv_info)
        self.assertFalse(c._event_info)

    def test_offline(self):
        (info, events) = get_data_file_text("single-controller-offline.txt")

        c = storcli_check.Controller(info, events, self.logger)
        result, errors = c.ok()
        self.assertFalse(result)
        self.assertTrue(len(errors) == 3)
        self.assertTrue("ofln" in errors[0])
        self.assertTrue("offln" in errors[1])
        self.assertTrue("offln" in errors[2])

        self.assertTrue("Controller" in repr(c))
        self.assertTrue(len(c._vd_info) == 2)
        self.assertTrue(len(c._pd_info) == 16)
        self.assertTrue(c._cv_info)
        self.assertFalse(c._event_info)

    def test_missing_drive_count(self):
        (info, events) = get_data_file_text("single-controller-missing-drive-count.txt")

        c = storcli_check.Controller(info, events, self.logger)
        result, errors = c.ok()
        self.assertTrue(result)
        self.assertTrue(len(errors) == 0)
        self.assertTrue("Controller" in repr(c))
        self.assertTrue(len(c._vd_info) == 2)
        self.assertTrue(len(c._pd_info) == 16)
        self.assertTrue(c._cv_info)
        self.assertFalse(c._event_info)

    def test_offline_wrong_pd_regex(self):
        """Test the case where we don't know how to parse the PD line"""
        (info, events) = get_data_file_text("single-controller-offline-pd-not-parsed.txt")

        self.assertRaises(Exception, storcli_check.Controller, info, events, self.logger)

    def test_offline_wrong_vd_regex(self):
        """Test the case where we don't know how to parse the PD line"""
        (info, events) = get_data_file_text("single-controller-offline-vd-not-parsed.txt")

        self.assertRaises(Exception, storcli_check.Controller, info, events, self.logger)

    def test_report_as_html(self):
        (info, events) = get_data_file_text("single-controller-offline.txt")
        c = storcli_check.Controller(info, events, self.logger)
        report = c.report_as_html()

        for substring in [
            "<b>PD Status</b>", "24:15&nbsp;&nbsp;&nbsp;&nbsp;15&nbsp;Onln",
            "1/1&nbsp;&nbsp;&nbsp;RAID10&nbsp;OfLn", "Firmware Package:"
        ]:
            self.assertTrue(substring in report)

    def test_bad_events(self):
        (info, events) = get_data_file_text("single-controller.txt", "bad-events.txt")

        c = storcli_check.Controller(info, events, self.logger)
        result, errors = c.ok()
        self.assertFalse(result)
        self.assertTrue(errors)
        self.assertTrue("Controller" in repr(c))
        self.assertTrue(len(c._vd_info) == 2)
        self.assertTrue(len(c._pd_info) == 16)
        self.assertTrue(c._cv_info)
        self.assertTrue(len(c._event_info) == 3)

    def test_invalid_events(self):
        # If the events file is invalid, there should be no events
        (info, events) = get_data_file_text("single-controller.txt", "invalid-events.txt")

        c = storcli_check.Controller(info, events, self.logger)
        result, errors = c.ok()
        self.assertTrue(result)
        self.assertFalse(errors)


if __name__ == '__main__':
    unittest.main()
