# TODO:
# - Front matter documentation.
# - Actions should be loaded from a python file provided via the command line.
# - Alert email from address should be configurable from the command line.
# - It should be possible to disable the alert emails.
# - The logging level should be configurable from the command line.

import BaseHTTPServer
import os
import sys
import time
import urlparse
import json
import argparse
import sh
import logging
import smtplib
from abc import ABCMeta, abstractmethod
from email.mime.text import MIMEText

# The path to this file.
scriptpath = os.path.realpath(__file__) 

# Initialize pythons logging facilities.
logging.basicConfig(
    filename=None,
    # MOD: Change to alter logging verbosity. Options are:
    # -logging.NOTSET
    # -logging.DEBUG
    # -logging.INFO
    # -logging.WARNING
    # -logging.ERROR
    # -logging.CRITICAL
    level=logging.DEBUG,
    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    datefmt='%m-%d %H:%M')

# Configure the command line interface.
parser = argparse.ArgumentParser(
'''A webserver that will map github webhook post requests to python code. The
mapping can be modified by modifying this script.''')
parser.add_argument("address",
                    help="IP or DNS name this webserver will bind to.")
parser.add_argument("port",help="Port number to bind to.",type=int)
args = parser.parse_args()

# The base class that all actions should extend.
class Action():
    '''An abstract class that represents an action to be taken on a webhook post
    that matches certain criteria.
    '''

    def __init__(self,uid,sp,hdrs,json):
        '''Initialize an action.
        Arguments:
        self -- Reference to "this" object.
        uid  -- Some unique identifier for a webhook post.
        sp   -- The path to the calling script.
        hdrs -- A dictionary mappy HTTP headers to values.
        json   -- The payload as a JSON object. Key-value pairs are accessible
                via the dictionary interface.
        '''
        self.uid = uid
        self.scriptpath = sp
        self.headers = hdrs
        self.json = json

    def log(self,lvl,msg):
        '''Print a log mesage with information specific to an action.
        Arguments:
        self -- Refence to "this" object.
        lvl  -- The logging level of this message.
        msg  -- The message to be logged.
        '''
        logging.log(lvl,
                    "[UID=%s,PID=%s,Action=%s] %s" 
                      % (self.uid,os.getpid(),self.__class__.__name__,msg))


    @abstractmethod
    def info(self):
        '''Information to place in an alert email sent to repository users.'''
        pass

    @abstractmethod
    def match(self):

        '''Return true if this action should be performed. Return false
        otherwise.
        Arguments:
        self -- Reference to "this" object.
        '''
        pass

    @abstractmethod
    def act(self):
        '''Return true if this action should be performed. Return false
        otherwise.
        Arguments:
        self -- Reference to "this" object.
        '''
        pass
            

    

# The action list will store actions to be run.
actionlist = []

class CloneAction(Action):
    ''' This class demonstrates how to write an action.'''

    def match(self):
        ''' Match push github events.'''
        self.alert = ""
        self.log(logging.DEBUG,
            "Checking if delivery %s from repo %s should be acted upon" 
              % (self.uid,self.json['repository']['url']))
        if self.headers['X-GitHub-Event'] == 'push':
            self.alert += "Push action received, this action should run.\n"
        else:
            self.alert += "Push action received, this action should not run.\n"
        return self.headers['X-GitHub-Event'] == 'push'

    def act(self):
        '''Clone the repository if it has not already be cloned.'''
        repo_name = self.json['repository']['name']
        repo_url = ("git@github.umn.edu:" + 
                    self.json['repository']['organization'] + 
                    "/" + 
                    self.json['repository']['name'])
        git = sh.git.bake()
        self.log(logging.DEBUG,
                 "checking for repo  %s in %s" % (repo_name, sh.pwd()))
        if not os.path.exists(repo_name):
            self.log(logging.DEBUG,"Cloning new repository")
            try:
                git.clone(repo_url)
                self.alert += "Cloned repository at %s" % repo_url
                self.log(logging.DEBUG,"Git clone succeeded.")
            except:
                msg = ("Attempt to clone repository at %s: %s" 
                       % (repo_url,sys.exc_info()[0]))
                self.log(logging.ERROR,msg)
                self.alert += msg
        else:
            msg = "Directory already exists, ignoring clone request of repository %s.\n" % repo_url 
            self.alert += msg
            self.log(logging.WARN,msg)

    def info(self):
        '''Report pertinent information back to the user.'''
        return self.alert

actionlist.append(CloneAction)

class HookHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    server_version = "Handler/0.1"

    # NB: Some events do not have an appropriate email address readily
    # available.
    def getEmailAddy(self,hdrs,json):
        if hdrs['X-GitHub-Event'] == 'push':
            return json['head_commit']['author']['email']
        else:
            return None

    def routeToAction(self,hdrs,json):
        global action
        global scriptpath
        content = ("Handling %s event from repository %s.\n\n"
                   % (hdrs['X-GitHub-Event'],json['repository']['url']))
        for ac in actionlist:
            a = ac(hdrs['X-GitHub-Delivery'],scriptpath,hdrs,json)
            if a.match():
                a.act()
            content += "Messages related to %s.\n" % a.__class__.__name__
            content += "=================================================\n"
            content += a.info()
            content += "\n=================================================\n"
                      
        addy = self.getEmailAddy(hdrs,json)
        if addy != None:
            email = MIMEText(content)
            email['Subject'] = ("GitHub Webhook Handler: %s from %s received.\n"
                                % (hdrs['X-GitHub-Event'],json['repository']['url']))
            # XXX: Should be configurable from the command line.
            email['From'] = "csci2041@cs.umn.edu"
            email['To'] = addy
            s = smtplib.SMTP('localhost')
            s.sendmail("csci2041@cs.umn.edu", addy, email.as_string())

    def do_GET(self):
        logging.info("Received get request with the following headers: %s" % self.headers)
        content_len = int(self.headers.getheader('content-length', 0))
        get_body = self.rfile.read(content_len)
        logging.info("Received get request with the following body: %s" % get_body)
        logging.warning("Ignoring get request.")
        self.send_response(200)

    def do_POST(self):
        # Check that the IP is within the GH ranges
        if not any(self.client_address[0].startswith(IP)
                   for IP in ('134.84.231')):
            logging.warning("Received post request from invalid IP!")
            self.send_error(403)

        logging.info("Received post request with the following headers: %s" % self.headers)
        content_len = int(self.headers.getheader('content-length', 0))
        payload = json.loads(self.rfile.read(content_len))
        logging.info("Received post request with the following JSON body: %s" % payload)
        logging.info("Forking to route and execute actions")
        pid = os.fork()
        if pid == 0:
            self.routeToAction(self.headers,payload)
            os._exit(0)
        else:
            logging.info("Routing being handled by process %s" %pid)
            self.send_response(200)

if __name__ == '__main__':
    server_class = BaseHTTPServer.HTTPServer
    httpd = server_class((args.address, int(args.port)), HookHandler)
    logging.info("Server started at %s:%s"% (args.address, int(args.port)))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Server stopped at %s:%s"% (args.address, int(args.port)))
