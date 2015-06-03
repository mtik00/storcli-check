#!/usr/bin/env python2.4
"""
This script is used to check the state of the MR controller on any system
running Python 2.4.
"""

# Imports ######################################################################
import os
import re
import sys
import socket
import logging
import smtplib
import zipfile
import subprocess
from getpass import getuser
from optparse import OptionParser
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders


# Metadata #####################################################################
__author__ = "Timothy McFadden"
__creationDate__ = "06/02/2015"
__license__ = "MIT"
__version__ = "0.01"

# Configuration ################################################################
CONTROLLER_OK_STATUSES = ["optimal"]
CV_OK_STATES = ["optimal"]
VD_OK_STATES = ["optl"]
PD_OK_STATES = ["onln", "ugood"]
DEFAULT_FROM = "%s@%s" % (getuser(), socket.gethostname())
LOGFILE = os.path.join(os.sep, "var", "log", "storcli-check.log")
################################################################################
DEBUG_FILE = None  # Set this to a captured output of "storcli64 /call show all"
CONTROLLER_RE = re.compile("""""")

INFO_RE = re.compile("""
    ^Model\s=\s(?P<model>.*?)$                              .*
    ^Serial\sNumber\s=\s(?P<serial>.*?)$                    .*
    ^SAS\sAddress\s=\s(?P<sasaddress>.*?)$                  .*
    ^Firmware\sPackage\sBuild\s=\s(?P<fw_package>.*?)$      .*
    ^Controller\sStatus\s=\s(?P<ctrl_status>.*?)$           .*
""", re.VERBOSE | re.MULTILINE | re.DOTALL | re.IGNORECASE)
VD_INFO_LINE_RE = re.compile("""
    ^(?P<dg>\d+)/(?P<vd>\d+)    \s+
    (?P<type>.+?)               \s+
    (?P<state>.+?)              \s+
    (?P<access>.+?)             \s+
    (?P<consistent>.+?)         \s+
    (?P<cache>.+?)              \s+
    (?P<scc>.+?)                \s+
    (?P<size>.+?\s[MGT]B)       \s*
""", re.VERBOSE | re.IGNORECASE)
PD_INFO_LINE_RE = re.compile("""
    ^(?P<enclosure>\d+):(?P<slot>\d+)   \s+
    (?P<devid>\d+)                      \s+
    (?P<state>.+?)                      \s+
    (?P<drive_group>-|\d+?)             \s+
    (?P<size>.+?\s[MGT]B)               \s+
    (?P<interface>.+?)                  \s+
    (?P<medium>.+?)                     \s+
    (?P<sed>.+?)                        \s+
    (?P<pi>.+?)                         \s+
    (?P<sector_size>.+?)                \s+
    (?P<model>.+?)                      \s+
    (?P<spun>.+?)                       \s*
""", re.VERBOSE | re.IGNORECASE)
CACHEVAULT_LINE_RE = re.compile("""
   ^(?P<model>.+?)\s+
    (?P<state>.+?)\s+
    (?P<temp>\d+C)\s+
    (?P<mode>.+?)\s+
    (?P<mfg_date>.+?)\s*
""", re.VERBOSE | re.IGNORECASE)


def find_storcli(logger, names=["storcli", "storcli64"]):
    """Look for the storcli application.  This is a little tricky because we
    may be running from cron (which has a very different path).
    """

    if "win" in sys.platform:
        names = ["%s.exe" % x for x in names]

    # Let the user use CWD
    for name in names:
        if os.path.exists(name):
            logger.debug("found %s", name)
            return os.path.abspath(os.path.join(".", name))

    # Search the default location of the RPM
    default_paths = [
        os.path.join(os.sep, "opt", "MegaRAID", "storcli", x)
        for x in names]

    for path in default_paths:
        if os.path.exists(path):
            logger.debug("found %s", path)
            return path

    for name in names:
        result = execute("which %s" % name)
        if "no %s" % name not in result:
            logger.debug("found %s", result)
            return result

    logger.error("Can't find storcli64")
    raise Exception


def get_logger(name=None, screen_level=logging.INFO,
               logfile_path=None, logfile_level=logging.DEBUG,
               logfile_mode="ab"):
    """Initializes the logging object.

    :param str name: The name of the logger; defaults to the script name
    :param int screen_level: The level of the screen logger
    :param str logfile_path: The path of the log file, if any
    :param int logfile_level: The level of the file logger
    :param str logfile_mode: The file mode of the file logger
    """
    if not name:
        name = os.path.splitext(os.path.basename(__file__))[0]

    _format = "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
    _logger = logging.getLogger(name)
    _logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    screen_formatter = logging.Formatter(_format)
    ch.setFormatter(screen_formatter)
    ch.setLevel(screen_level)
    _logger.addHandler(ch)

    if logfile_path:
        logfile_formatter = logging.Formatter(_format)
        fh = logging.FileHandler(logfile_path, logfile_mode)
        fh.setLevel(logfile_level)
        fh.setFormatter(logfile_formatter)
        _logger.addHandler(fh)

    return _logger


def flush_logfile(logger):
    """Finds any FileHandlers and flushes them."""
    for handler in [x for x in logger.handlers if isinstance(x, logging.FileHandler)]:
        handler.flush()


def remove_directory(top, remove_top=True, filter=None):
    '''
    Removes all files and directories, bottom-up.

    :param str top: The top-level directory to clean out
    :param bool remove_top: Whether or not to delete the top
        directory when cleared.
    :param code filter: A function that returns True or False
        based on the name of the file or folder.  Returning
        True means "delete it", False means "keep it".
    '''
    if filter is None:
        filter = lambda x: True

    for root, dirs, files in os.walk(top, topdown=False):
        for name in [x for x in files if filter(x)]:
            os.remove(os.path.join(root, name))

        for name in [x for x in dirs if filter(x)]:
            os.rmdir(os.path.join(root, name))

    if remove_top:
        os.rmdir(top)


def zip(items, destination):
    '''Zip up all request items into a single file.  We will attempt to use the
    zipfile package.  However, there's a bug in 2.7 where files > 4G will not
    work (http://bugs.python.org/issue9720).
    '''
    def add_directory(zipfile_obj, source_dir, dest_dir):
        '''Walk a directory and add all files to the zipfile.'''
        rootlen = len(source_dir) + 1
        for base, dirs, files in os.walk(source_dir):
            for item in [x for x in files]:
                fn = os.path.join(base, item)
                zipfile_obj.write(fn, dest_dir + fn[rootlen:])

    myzip = zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED)

    try:
        for item in items:
            if os.path.isdir(item):
                add_directory(myzip, item, item + os.sep)
            else:
                myzip.write(item)
    finally:
        myzip.close()

    if not os.path.isfile(destination):
        raise Exception("Zip file was not created")  # pragma: no cover


def execute(command, cwd=None):
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=cwd)
    out, _ = p.communicate()

    return out.strip()


def sendmail(subject, to, sender, body, mailserver, body_type="html", attachments=None, cc=None):
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(to)

    if cc:
        msg['Cc'] = ", ".join(cc)
    else:
        cc = []

    msg.attach(MIMEText(body, body_type))

    attachments = [] or attachments

    for attachment in attachments:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(attachment, "rb").read())
        Encoders.encode_base64(part)

        part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment))

        msg.attach(part)

    server = smtplib.SMTP(mailserver)
    server.sendmail(sender, to + cc, msg.as_string())  # pragma: no cover


class Controller(object):
    def __init__(self, show_all_data, logger):
        self._cached_info = show_all_data
        self._logger = logger

        self._basic_data = {}
        self._vd_info = []
        self._pd_info = []
        self._cv_info = {}

        self.vd_list = "--- no virtual drives found ---"
        self.pd_list = "--- no physical drives found ---"
        self.cv_list = "--- no Cachevault found ---"
        self._parse()
        self._check()

    def __repr__(self):
        return "Controller(%s)" % self._basic_data.get("sasaddress", "unknown")

    def _parse(self):
        """Parsed the output of the "show all" command into Python types"""
        self._logger.debug("begin parse")
        try:
            self._basic_data = INFO_RE.search(self._cached_info).groupdict()

            vd_count_match = re.search("Virtual Drives = (\d+)", self._cached_info, re.IGNORECASE)
            if vd_count_match:
                vd_count = int(vd_count_match.group(1))
            else:
                vd_count = None

            match = re.search("^VD\sLIST.*?===$(.*?)Cac=", self._cached_info, re.MULTILINE | re.DOTALL)
            if match:
                self.vd_list = match.group(1)
                for line in self.vd_list.split("\n"):
                    match = VD_INFO_LINE_RE.search(line)
                    if match:
                        self._vd_info.append(match.groupdict())

            # Make sure we parse each VD line
            if vd_count and (len(self._vd_info) != vd_count):
                self._logger.error("Unparsed VDs on: %s", self)
                raise Exception("Unparsed VDs on: %s" % self)

            pd_count_match = re.search("Physical Drives = (\d+)", self._cached_info, re.IGNORECASE)
            if pd_count_match:
                pd_count = int(pd_count_match.group(1))
            else:
                pd_count = None

            match = re.search("^PD\sLIST.*?===$(.*?)EID-", self._cached_info, re.MULTILINE | re.DOTALL)
            if match:
                self.pd_list = match.group(1)

                for line in self.pd_list.split("\n"):
                    match = PD_INFO_LINE_RE.search(line)
                    if match:
                        self._pd_info.append(match.groupdict())

            # Make sure we parse each PD line
            if pd_count and (len(self._pd_info) != pd_count):
                self._logger.error("Unparsed PDs on: %s", self)
                raise Exception("Unparsed PDs on: %s" % self)

            match = re.search("^Cachevault.Info.*?(---.*---$)", self._cached_info, re.MULTILINE | re.DOTALL)
            if match:
                self.cv_list = match.group(1)
                for line in self.cv_list.split("\n"):
                    match = CACHEVAULT_LINE_RE.search(line)
                    if match:
                        self._cv_info = match.groupdict()
                        break

            self._parsed = True
        except Exception, e:
            self._logger.error(e)
            raise

        self._logger.debug("...ok")

    def _check(self):
        """Checks the state and status of the controller and all virtual/physical
        drives.
        """
        self._logger.debug("begin OK check")
        result = True
        errors = []

        if self._basic_data["ctrl_status"].lower() not in CONTROLLER_OK_STATUSES:
            errors.append("%r status: '%s' not in %s" % (
                self,
                self._basic_data["ctrl_status"].lower(),
                CONTROLLER_OK_STATUSES))
            result = False

        if not self._vd_info:
            errors.append("WARNING: No VD info!")
        else:
            for info in self._vd_info:
                if str(info["state"]).lower() not in VD_OK_STATES:
                    errors.append("VD(%s/%s) state: '%s' not in %s" % (
                        info.get("dg", "?"),
                        info.get("vd", "?"),
                        info.get("state", "?").lower(),
                        VD_OK_STATES))
                    result = False

        if not self._pd_info:
            errors.append("WARNING: No PD info!")
        else:
            for info in self._pd_info:
                if str(info["state"]).lower() not in PD_OK_STATES:
                    errors.append("PD(%s:%s [devid %s]) state: '%s' not in %s" % (
                        info.get("enclosure", "?"),
                        info.get("slot", "?"),
                        info.get("devid", "?"),
                        info.get("state", "?").lower(),
                        PD_OK_STATES))
                    result = False

        if result:
            self._logger.debug("...pass")
        else:
            for error in errors:
                self._logger.debug("...%s", error)

            self._logger.warn("!!!FAIL!!!")

        self.result, self.errors = result, errors

    def ok(self):
        return (self.result, self.errors)

    def report_as_html(self):
        """Generates an HTML report of the state of the topology."""

        body = """
        <h1>Controller Status</h1>
        <pre>
Status: %s
Model: %s
SAS Address: %s
Firmware Package: %s
        </pre>
        <b>VD Status</b>
        <pre>%s</pre>
        <b>PD Status</b>
        <pre>%s</pre>
        <b>CV Info</b>
        <pre>%s</pre>
        """ % (
            self._basic_data["ctrl_status"], self._basic_data["model"],
            self._basic_data["sasaddress"], self._basic_data["fw_package"],
            self.vd_list,
            self.pd_list,
            self.cv_list
        )

        if self.errors:
            body += "<b>Errors</b><pre>\n%s</pre>" % "\n".join(self.errors)

        return body


class StorCLI(object):
    def __init__(self, path, logger, working_directory=None, debug_file=None):
        """This object is used to interact with the LSI storcli utility and parse
        its output.

        :param str path: The path of the storcli/storcli64 binary
        :param str working_directory: The working directory to run the storcli
            commands and store the output of the "show all" command.
        :param logging logger: The logger to use
        """
        super(StorCLI, self).__init__()
        self._path = path
        self._logger = logger
        self._cached_info = None
        self._parsed = False
        self._working_directory = working_directory or os.getcwd()

        self._controllers = []

        self._load(debug_file)

    def _command(self, command):
        """Execute a generic command on the command line and return the result"""
        command = "%s %s" % (self._path, command)
        return execute(command, cwd=self._working_directory)

    def _load(self, debug_file=None):
        """Run the "show all" command, store it to a text file, then parse the
        text.
        """
        if debug_file:
            fh = open(debug_file, "rb")
            self._cached_info = fh.read()
            fh.close()
            self._logger.debug("read [%s]", debug_file)
        else:
            self._cached_info = self._command("/call show all")
            temp_file = os.path.join(self._working_directory, "show-all.txt")
            fh = open(temp_file, "wb")
            fh.write(self._cached_info)
            fh.close()

            self._logger.debug("wrote [%s]", temp_file)

        self._parse()
        self._check()

    def _parse(self):
        """Parsed the output of the "show all" command into Python types"""
        self._logger.debug("begin parse")
        for controller_text in re.split("Basics\s:", self._cached_info, re.MULTILINE)[1:]:
            self._controllers.append(Controller(controller_text, logger=self._logger))

        self._logger.debug("...ok")

    def _check(self):
        """Checks the state and status of the controller and all virtual/physical
        drives.
        """
        self.errors = []
        self.result = True

        self._logger.debug("begin OK check")
        for controller in self._controllers:
            result, errors = controller.ok()

            self.result &= result
            self.errors += errors

    def ok(self):
        return (self.result, self.errors)

    def report_as_html(self):
        """Generates an HTML report of the state of the topology."""
        body = ""
        subject = "%s MR Check Result: PASS" % socket.gethostname()

        for controller in self._controllers:
            result, errors = controller.ok()

            if not result:
                subject = "%s MR Check Result: FAIL" % socket.gethostname()

            body += controller.report_as_html()

        return (subject, body)


def parse_arguments(parser, logger, args=None):
    result = True

    (options, args) = parser.parse_args(args)
    logger.debug("options: %s; args: %s", options, args)

    for variable in ["mail_to", "mail_server"]:
        if not getattr(options, variable, None):
            logger.error("command-line argument [%s] is required", variable)
            result = False

    if not result:
        parser.print_help()
        sys.exit(-1)

    return (options, args)


def init_parser():
    parser = OptionParser(version=__version__)
    parser.add_option(
        "--to", dest="mail_to",
        help="REQUIRED: comma-separated list of email addresses to send the report to")
    parser.add_option(
        "--mailserver", dest="mail_server",
        help="REQUIRED: The hostname of the SMTP server to use (e.g. 'mailhost.example.com')")
    parser.add_option(
        "--force", dest="force", action="store_true",
        help="send the report regardless of the result")
    parser.add_option(
        "--from", dest="mail_from",
        help="the 'user' sending the report (defaults to %s)" % DEFAULT_FROM,
        default=DEFAULT_FROM)
    parser.add_option(
        "--cc", dest="mail_cc",
        help="comma-separated list of email addresses to CC the report to",
        default="")
    parser.add_option(
        "--debug-print", dest="debug_print", action="store_true",
        help="skip the email and print the body on the command line")
    return parser


if __name__ == '__main__':
    import tempfile

    # DEBUG_FILE = "/mnt/validation-fs/home/tim/dump.txt"

    # Create a temporary directory to store all of our stuff
    working_directory = tempfile.mkdtemp()
    logger = get_logger(logfile_path=LOGFILE, logfile_mode="ab")
    logger.debug("================================= Start of script ==========")
    logger.debug("using working directory: [%s]", working_directory)

    parser = init_parser()
    (options, args) = parse_arguments(parser, logger)

    if options.debug_print:
        print working_directory

    storcli_path = find_storcli(logger)
    s = StorCLI(
        path=storcli_path,
        working_directory=working_directory,
        logger=logger,
        debug_file=DEBUG_FILE)
    result, errors = s.ok()

    if not result or options.force:
        zipdir = tempfile.mkdtemp()
        log_path = os.path.abspath(os.path.join(zipdir, "logs.zip"))
        flush_logfile(logger)
        zip([working_directory, LOGFILE], log_path)
        subject, body = s.report_as_html()

        if options.debug_print:
            print body
        else:
            sendmail(
                subject=subject,
                to=options.mail_to.split(","),
                body=body,
                sender=options.mail_from,
                mailserver=options.mail_server,
                attachments=[log_path],
                cc=options.mail_cc.split(","))

        remove_directory(zipdir)

    remove_directory(working_directory)

    sys.exit(0)
