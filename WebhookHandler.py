import BaseHTTPServer
import os
import sys
import time
import urlparse
import json
import argparse
import sh
import logging
from abc import ABCMeta, abstractmethod

# Initialize pythons logging facilities.
logging.basicConfig(
    filename=None,
    level=logging.DEBUG,
    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    datefmt='%m-%d %H:%M')

# Configure the command line interface
parser = argparse.ArgumentParser(
'''A webserver that will map github webhook post requests to python code. The
mapping can be modified by modifying this script.''')
parser.add_argument("address", help="IP or DNS name this webserver will bind to.")
parser.add_argument("port",help="Port number to bind to.",type=int)
args = parser.parse_args()

# The base class that all actions should extend.
class Action():
    '''An abstract class that represents an action to be taken on a webhook post that matches certain criteria.'''
    @abstractmethod
    def match(self,headers,payload):
        '''Return true if this action should be performed. Return false otherwise.'''
        pass

    @abstractmethod
    def act(self,headers,payload):
        '''If the post request matched this action then perform the action.'''
        pass
        

# The action list will store actions to be run
actionlist = []

class ExampleAction(Action):

    def debug(self, string):
        logging.debug("[ExampleAction] %s" % string)

    def match(self,headers,json):
        self.debug(
            "Checking if delivery %s from repo %s should be acted upon" 
              % (headers['X-GitHub-Delivery'],json['repository']['url']))
        return headers['X-GitHub-Event'] == 'push'

    def act(self,headers,json):
        repo_name = json['repository']['name']
        repo_url = "git@github.umn.edu:" + json['repository']['organization']+ "/" +json['repository']['name']
        git = sh.git.bake()
        self.debug("checking for repo  %s in %s" % (repo_name, sh.pwd()))
        if not os.path.exists(repo_name):
            self.debug("Cloning new repository")
            self.debug("Git clone results of %s: %s" 
                         %(headers['X-GitHub-Delivery'],git.clone(repo_url)))

actionlist.append(ExampleAction())

class HookHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    server_version = "HookHandler/0.1"

    def routeToAction(self,headers,json):
        global action
        for a in actionlist:
            if a.match(headers,json):
                a.act(headers,json)

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
