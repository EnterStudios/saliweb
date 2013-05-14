#!/usr/bin/python

"""Simple functions to run jobs on Sali Lab REST web services.

   This file contains a number of functions to submit jobs to Sali Lab
   REST web services, and to extract results.

   This file can also be run directly, in which case it presents a similar
   command line interface to the services.
"""

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Copyright (c) 2012 Sali Lab

import sys
import os
from xml.dom.minidom import parseString
import xml.parsers.expat
import subprocess
import urllib2
import time

def _curl_rest_page(url, curl_args):
    # Sadly Python currently has no method to POST multipart forms, so we
    # use curl instead
    p = subprocess.Popen(['curl', '-s'] + curl_args \
                          + [url], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    exitval = p.wait()
    if exitval != 0:
        raise OSError("curl failed with exit %d; stderr:\n%s" % (exitval, err))
    try:
        dom = parseString(out)
    except xml.parsers.expat.ExpatError:
        print >> sys.stderr, "Web service did not return valid XML:\n" + out
        raise
    top = dom.getElementsByTagName('saliweb')
    if len(top) == 0:
        raise ValueError("Invalid XML: web service did not return "
                         "XML containing a 'saliweb' tag")
    return top[0], out

class _Parameter(object):
    def __init__(self, name, help, optional):
        self.name = name
        self.help = help
        self.optional = optional == '1'
    def get_full_arg(self):
        a = self._get_arg()
        if self.optional:
            return '[' + a + ']'
        else:
            return a
    def _get_arg(self):
        return '%s=ARG' % self.name
    def get_help(self):
        h = "%-20s" % self.name + self.help
        if self.optional:
            h += ' [optional]'
        return h

class _FileParameter(_Parameter):
    def _get_arg(self):
        return '%s=@FILENAME' % self.name

def _get_parameters_from_xml(xml):
    ps = []
    for param in xml.getElementsByTagName('parameters'):
        for c in param.childNodes:
            if c.nodeName == 'string':
                ps.append(_Parameter(c.getAttribute('name'),
                                     c.childNodes[0].wholeText,
                                     c.getAttribute('optional')))
            elif c.nodeName == 'file':
                ps.append(_FileParameter(c.getAttribute('name'),
                                         c.childNodes[0].wholeText,
                                         c.getAttribute('optional')))
    return ps

def show_info(url):
    """Given the URL of a Sali lab web service, print information about it."""
    progname = os.path.basename(sys.argv[0])
    p, out = _curl_rest_page(url, [])
    service = p.getElementsByTagName('service')[0].getAttribute('name')
    parameters = _get_parameters_from_xml(p)
    if parameters:
        pstr = " ".join(x.get_full_arg() for x in parameters)
    else:
        pstr = "[name1=ARG] [name2=@FILENAME] ..."
    print "\nSali Lab %s web service." % service
    print "\nTo submit a job to this web service, run:\n"
    print "%s submit %s " % (progname, url) + pstr
    print
    print "Where ARG is a string argument, and FILENAME is the name of a "
    print "file to upload (note the '@' prefix)."
    if parameters:
        for x in parameters:
            print "   " + x.get_help()
    else:
        print """
To determine name1, name2 etc., view the HTML source of the regular web
service page and look at the names of the HTML form elements. Alternatively,
ask the developer of the web service to implement the
get_submit_parameter_help() method!"""

def submit_job(url, args):
    """Submit a job to a Sali Lab web service (but don't wait for it to end).
       'args' is a service-dependent list of arguments; each should be suitable
       for passing to curl as an argument to its -F option (e.g. 'foo=bar' sets
       the 'foo' variable to 'bar'; 'foo=@bar' uploads the file 'bar' as the
       'foo' variable). Use show_info() to determine the variable names.
       (Note that the more natural Python keyword syntax, e.g. foo='bar',
       is not used, since it is possible for HTML names to be invalid Python
       keywords.)

       On successful execution, the job is started, and a URL is returned
       at which results will appear (use get_results() to query it).
    """
    curl_args = []
    for a in args:
        curl_args.append('-F')
        curl_args.append(a)
    p, out = _curl_rest_page(url, curl_args)
    for results in p.getElementsByTagName('job'):
        url = results.getAttribute('xlink:href')
        print "Job submitted: results will be found at " + url
        return url
    raise IOError("Could not submit job: " + out)

def get_results(url):
    """Check for results from a web service.
       Given a URL previously returned by submit_job(), this returns a list
       of URLs, each pointing to an output file generated by the web service.
       If the job hasn't finished yet, None is returned.
    """
    try:
        u = urllib2.urlopen(url)
    except urllib2.HTTPError, detail:
        if detail.code == 503:
            print "Job not done yet"
            return
        else:
            raise
    dom = parseString(u.read())
    print "Got results:"
    urls = []
    top = dom.getElementsByTagName('saliweb')[0]
    for results in top.getElementsByTagName('results_file'):
        url = results.getAttribute('xlink:href')
        urls.append(url)
        print "   " + url
    dom.unlink()
    return urls

def run_job(url, args):
    """Run a job, wait for it to finish, and return its results.
       This is essentially the same as running submit_job(), then
       periodically running get_results() until results become available.
    """
    results_url = submit_job(url, args)
    interval = 10
    while True:
        time.sleep(interval)
        if interval < 1200:
            interval = interval * 3 / 2
        results = get_results(results_url)
        if results is not None:
            return results

class _Command(object):
    def __init__(self, progname, usage_prefix):
        self.progname = progname
        self.usage_prefix = usage_prefix
    def usage(self):
        print "\nUsage: %s " % self.usage_prefix + self.usage_args \
              + '\n\n' + self.long_help.replace('%prog', self.progname)

class _InfoCommand(_Command):
    short_help = "Get basic information about a web service."
    usage_args = '<url>'
    long_help = short_help + """
<url> should be the REST URL for a Sali Lab web service. This is generally
the same as the main web page, with /job appended. For example, to access the
ModLoop server, use http://salilab.org/modloop/job (the main web page is
at http://salilab.org/modloop/).

If the URL is valid and the web service is working properly, this will show
a sample usage for submitting jobs to the service.
"""
    def main(self, args):
        if len(args) == 1:
            show_info(args[0])
        else:
            self.usage()
            sys.exit(1)

class _SubmitCommand(_Command):
    short_help = "Submit a job to a web service (don't wait for it to finish)."
    usage_args = '<url> [ARGS ...]'
    long_help = short_help + """
<url> identifies the web service to submit to (see '%prog help info'
for more information). The additional arguments depend on the service;
the output of '%prog info <url>' suggests suitable arguments.

This only submits the job; on successful completion, a new URL is returned,
at which the results will become available when the job completes. Use
'%prog results' to check for these results.
"""
    def main(self, args):
        if len(args) >= 1:
            submit_job(args[0], args[1:])
        else:
            self.usage()
            sys.exit(1)

class _ResultsCommand(_Command):
    short_help = "Check for web service results."
    usage_args = '<url>'
    long_help = short_help + """
<url> should be the URL returned by a previous call to '%prog submit'.
If the job has finished, a list of URLs of job outputs will be returned.
"""
    def main(self, args):
        if len(args) == 1:
            get_results(args[0])
        else:
            self.usage()
            sys.exit(1)

class _RunCommand(_Command):
    short_help = "Run a web service job to completion."
    usage_args = '<url> [ARGS ...]'
    long_help = short_help + """
This starts a job and then waits until it has completed, finally returning the
results. It is basically the equivalent of calling '%prog submit',
followed by calling '%prog results' periodically until the
job finishes. See '%prog submit' for more information on
the parameters.
"""
    def main(self, args):
        if len(args) >= 1:
            run_job(args[0], args[1:])
        else:
            self.usage()
            sys.exit(1)


class _WebService(object):
    def __init__(self):
        self.short_help = "Run jobs using Sali lab REST web services."
        self._progname = os.path.basename(sys.argv[0])
        self._all_commands = {'info':_InfoCommand,
                              'submit':_SubmitCommand,
                              'results':_ResultsCommand,
                              'run':_RunCommand}

    def main(self):
        if len(sys.argv) <= 1:
            print self.short_help + " Use '%s help' for help." % self._progname
        else:
            command = sys.argv[1]
            if command == 'help':
                if len(sys.argv) == 3:
                    self.show_command_help(sys.argv[2])
                else:
                    self.show_help()
            elif command in self._all_commands:
                self.do_command(command)
            else:
                self.unknown_command(command)

    def show_help(self):
        print self.short_help + """

Usage: %s <command> [args]

Commands:""" % self._progname
        print "    %-8s  Get help on using %s." % ('help', self._progname)
        for (key, val) in self._all_commands.items():
            print "    %-8s  %s" % (key, val.short_help)
        print """
Use "%s help <command>" for detailed help on any command.""" % self._progname

    def show_command_help(self, command):
        if command == 'help':
            self.show_help()
        elif command in self._all_commands:
            c = self._all_commands[command](self._progname,
                                            self._progname + ' ' + command)
            c.usage()
        else:
            self.unknown_command(command)

    def do_command(self, command):
        c = self._all_commands[command](self._progname,
                                        self._progname + ' ' + command)
        c.main(sys.argv[2:])

    def unknown_command(self, command):
        print "Unknown command: '%s'" % command
        print "Use '%s help' for help." % self._progname
        sys.exit(1)

def main():
    ws = _WebService()
    ws.main()

if __name__ == '__main__':
    main()
