#!/usr/bin/env python2.4
"""
This script is used to create the release file.
"""

# Imports ######################################################################
import os


# Metadata #####################################################################
__author__ = "Timothy McFadden"
__creationDate__ = "06/08/2015"
__license__ = "MIT"


# Globals ######################################################################
THIS_DIR = os.path.abspath(os.path.dirname(__file__))
SRC = os.path.join(THIS_DIR, "..", "src", "storcli_check.py")
DEST_DIR = os.path.join(THIS_DIR, "..", "release")

if __name__ == '__main__':
    import imp
    import tarfile

    # Read the version from our project
    mod = imp.load_source("storcli_check", SRC)

    destination = os.path.join(DEST_DIR, "storcli_check-%s.tar.gz" % mod.__version__)
    with tarfile.open(destination, "w:gz") as tar:
        tar.add(SRC, "storcli_check.py")

    print "[%s] created" % destination
