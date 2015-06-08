#!/usr/bin/env python
__author__ = "Timothy McFadden"
__date__ = "06/08/2015"
__copyright__ = "Timothy McFadden, 2015"
__license__ = "MIT"
"""
This is the unit test for storcli_check.py
"""
import os
import sys
import logging
import unittest

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(THIS_DIR, "data", "multi-controller-fail-events")

sys.path.insert(0, os.path.abspath(os.path.join(THIS_DIR, '..')))
import storcli_check


class TestMain(unittest.TestCase):
    def setUp(self):
        self.logger = storcli_check.get_logger()
        self.logger.setLevel(logging.CRITICAL)
        self.storcli = storcli_check.StorCLI(None, self.logger, _debug_dir=DATA_DIR)

    def test_errors(self):
        result, errors = self.storcli.ok()
        self.assertFalse(result)
        self.assertTrue(errors)

    def test_controllers(self):
        # Our sample data has 1 good controller, 1 controller with no devices,
        # and one controller with bad events
        ok = [x for x in self.storcli._controllers if not x.errors]
        bad = [x for x in self.storcli._controllers if x.errors]

        self.assertTrue(len(ok) == 1)
        self.assertTrue(len(bad) == 2)

if __name__ == '__main__':
    unittest.main()
