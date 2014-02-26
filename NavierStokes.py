"""
NavierStokes.py
Author: Stephen J. Sekula
Created: Dec. 23, 2013

Purpose: Gathers messages from one social network and posts to others.
This is intended as a cross-posting tool, using the *Handler classes
for all the heavy lifting.
"""

import sys
import os
import re
import time
import getopt 
import logging
import ConfigParser
import codecs
import math

from os.path import expanduser
from lockfile import FileLock,LockTimeout

import requests
from requests_oauthlib import OAuth1

import GNUSocialTools
import PumpTools
import DiasporaTools

from MessageObj import Message

FORMAT = "%(asctime)-15s %(message)s"
logging.basicConfig(format=FORMAT,level=logging.INFO)

home = expanduser("~")

# Parse command line options
try:
    opts, args = getopt.getopt(sys.argv[1:], "dhi:o:", ["debug","help", "input=", "output="])
except getopt.GetoptError as err:
    # print help information and exit:
    print str(err) # will print something like "option -a not recognized"
    sys.exit(2)
    pass
output = None
input = None
verbose = False
debug = False
for o, a in opts:
    if o in ("-h", "--help"):
        sys.exit()
    if o in ("-d", "--debug"):
        debug = True
    elif o in ("-i", "--input"):
        input = a
    elif o in ("-o", "--output"):
        output = a
    else:
        assert False, "unhandled option"
        pass
    pass




sources_and_sinks = {}

# Use the config file to setup the sources and sinks
config = ConfigParser.ConfigParser()
config.read(home+'/.navierstokes/navierstokes.cfg')
    

for section in config.sections():
    logging.info("Configuring a handler named %s", section)
    if config.get(section, "type") == "gnusocial":
        sources_and_sinks[section] = GNUSocialTools.GNUSocialHandler(site=config.get(section, "site"), \
                                                                         username=config.get(section, "username"), \
                                                                         password=config.get(section, "password"))
        pass
    elif config.get(section, "type") == "pump.io":
        client_credentials = config.get(section, "client_credentials").split(',')
        client_tokens=config.get(section, "client_tokens").split(',')

        sources_and_sinks[section] = PumpTools.PumpHandler(webfinger=config.get(section, "webfinger"), \
                                                               credentials=client_credentials, \
                                                               tokens=client_tokens)
        pass
    elif config.get(section, "type") == "diaspora":
        sources_and_sinks[section] = DiasporaTools.DiasporaHandler(webfinger=config.get(section, "webfinger"), \
                                                                       password=config.get(section, "password"))
        pass
    pass

if debug == True:
    for handler in sources_and_sinks:
        logging.info("Seting %s to debug mode", handler)
        sources_and_sinks[handler].debug = debug
        pass


if not os.path.exists(home+'/.navierstokes/'):
    os.makedirs(home+'/.navierstokes/')
    pass



messagesToWrite = []

source = sources_and_sinks[input]
sinks = []

sinknames = []

if output != None:
    sinknames = output.split(',')
    pass

for sink in sinknames:
    sinks.append( sources_and_sinks[sink] )
    pass


# retrieve messages from source
messages = []

messages = source.gather()

# print time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(most_recent_message_time))
# print timestamp

# Acquire file lock on last_update file before trying to write any messages.
lock = FileLock(home+"/.navierstokes/last_update.txt")

while not lock.i_am_locking():
    try:
        lock.acquire(timeout=10)
    except LockTimeout:
        logging.error("Lock acquisition: %s", "Unable to acquire file lock needed for operations.")
        sys.exit()
        pass
    pass

last_update = open(home+'/.navierstokes/last_update.txt','r+')
timestamp = last_update.read()
timestamp = float(timestamp.rstrip('\n'))
last_update.close()

most_recent_message_time = timestamp
#current_time = time.time()+3600.0*6.0
current_time = time.mktime(time.gmtime())

for message in messages:


    print "Message UNIX Epoch: %f, and current time: %f" % (message.date,current_time)

    if (math.fabs(message.date - current_time))>3600:
        print "Message is too old - will not post to other services."
        continue

    if message.reply:
        continue
    
    if message.repost:
        message.content = 'I thought this, posted by <a href="%s">%s</a>, was interesting on %s: ' % (unicode(message.author_url).encode("utf-8"), unicode(message.author).encode("utf-8"), input) + message.content
        pass
    
    messagetime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(message.date))
    # print "   Message time: %s" % (messagetime)
    # print "               : %f" % (message.date)
    
    if message.date > timestamp:
        # print message.content
        if message.date > most_recent_message_time:
            most_recent_message_time = message.date
            pass
        messagesToWrite.append(message)
        pass
    
    pass

if len(sinks) == 0:
    lock.release()
    sys.exit()
    pass


for sink in sinks:
    logging.info("Handler::write: %s", "Writing message to " + sink.__class__.__name__)
    sink.write( messagesToWrite )
    pass

# Write the current time to the last_check.txt
last_update = open(home+'/.navierstokes/last_update.txt','w')
last_update.write(str(most_recent_message_time))
last_update.close()

lock.release()
