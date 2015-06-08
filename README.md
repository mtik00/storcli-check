# storcli-check
This is a Python 2.4-compatible script that will check your MegaRAID adapter
for issues and send a report by email.  It's designed to be self contained and
easily added to a cron job.

## Usage
The following command-line parameters are optional:
 - `--mailto`: Comma-separated list of emails to send the report to (e.g. `"first1.last1@example.com,first2.other2@example.com"`)
 - `--mailserver`:  The hostname of the SMTP server to use (e.g. "mailhost.example.com")
 - `--force`: Force the script to send the report even if everything's fine (useful for *weekly status*)
 - `--mailfrom`: The user the email will seem to come from.  The default is `<username>@<hostname>`.
 - `--mailcc`: Comma-separated list of emails to CC the report to (e.g. `"first1.last1@example.com,first2.other2@example.com"`)

 NOTE: If `--mailto` and `--mailserver` are ommited, `--debug-print` is implied.

## General Information
The script is a relatively simple parser and reporter for the `storcli /cx show all`
command.  It checks to ensure that the controller's status is "optimal", all
virtual drives are "optimal", and all physical drives are "online".

## The Report
The report that is emailed contains some controller information, the list of
VDs, and the list of PDs.  Any errors found during parsing are also reported.
You will also find a zip file the contains the output from `show all`, `show events`,
and also the `MegaSAS.log` file that `storcli` generates (one info and event file
for each controller).

## Real World
I'm using this script to check the state of my LSI controller on a XenServer
hypervisor.  It was a lot easier than trying to figure out how to pass the
controller to a guest VM and using MegaRAID Storage Manager, get MSM snmp installed
and running on the hypervisor, etc.  The requirements for this script are pretty
minimal (in my opinion), and it is working in my lab.

I have it periodically running via `cron`.  It's working so far!  I run the defaults
every 10 minutes (doesn't send logs if everything's ok), and `--force` the report
once per week:

    */10 * * *  *   root /usr/local/bin/storcli-check --to=me@example.com --mailserver=mailhost.example.com 2>/dev/null
    0  8  *  *  mon root /usr/local/bin/storcli-check --to=me@example.com --mailserver=mailhost.example.com --force 2>/dev/null

## Caveats

 - SMTP authentication: the SMTP mail server we are running does not require
authentication if the FROM and TO domains are *local*.  Therefore, I didn't add
authentication to `sendmail()`.
 - Any *offline* drive will be an error: In my particular case, all of my PDs
   are part of a volume.  If that's not the case in your configuration, you may
   want to modify which PD states are *OK* in your configuration.
 - The script was tested with storcli64 version 1.15.05.  Other versions may
   cause issues with the regular expressions.

## Configuration

If you find that the defaults don't work for you, you should be able to make modifications
in the *Configuration* section of the source.  I don't use any type of config file.
The section is near the top of the script.

## Events

An attempt is made to report possible event problems.  The following command is
run for each controller:

    /cx show events filter=warning,critical,fatal

If this command returns anything, the script will consider the controller to be
in an error state.  The script **never** clears the events.  This means that you
may get spammed depending on how often you: a) run the script; b) how quickly
you address the issue; c) how soon you clear the events.

Here's an example of a sequence of events that will be reported by this script:

    seqNum: 0x0000cf1a
    Time: Tue Jun  2 18:02:08 2015

    Code: 0x000000fb
    Class: 2
    Locale: 0x01
    Event Description: VD 00/0 is now DEGRADED
    Event Data:
    ===========
    Target Id: 0


    seqNum: 0x0000cf1d
    Time: Tue Jun  2 18:03:11 2015

    Code: 0x000000fc
    Class: 3
    Locale: 0x01
    Event Description: VD 00/0 is now OFFLINE
    Event Data:
    ===========
    Target Id: 0


    seqNum: 0x0000cf20
    Time: Tue Jun  2 18:03:35 2015

    Code: 0x000000fb
    Class: 2
    Locale: 0x01
    Event Description: VD 00/0 is now DEGRADED
    Event Data:
    ===========
    Target Id: 0

In this mock-scenario, we had two drives go offline, which brought the VD
offline.  We then replaced one of the drives, which moved the VD back into the
`DEGRADED` state.  Then we replaced the second drive, which moved the VD back
into the `OPTIMAL` state.  Notice, however, the `OPTIMAL` event was not captured.
It doesn't show up since that event is not *warning* or above.

It's not a perfect system, but it serves its purpose.  You'll need to clear the
event log of the offending controller to get the report to stop spamming your email.
