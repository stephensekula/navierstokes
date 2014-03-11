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
import calendar
import getopt 
import logging
import ConfigParser
import codecs
import math
import copy
import hashlib

from os.path import expanduser
from lockfile import FileLock,LockTimeout

import requests
from requests_oauthlib import OAuth1

import GNUSocialTools
import PumpTools
import DiasporaTools

from MessageObj import Message

# Fuzzy text matching
from fuzzywuzzy import fuzz
from fuzzywuzzy import process


FORMAT = "%(asctime)-15s %(message)s"
logging.basicConfig(format=FORMAT,level=logging.INFO)

home = expanduser("~")

# Create the configuration and data directory
if not os.path.exists(home+'/.navierstokes/'):
    os.makedirs(home+'/.navierstokes/')
    pass

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
fuzzy = False

for o, a in opts:
    if o in ("-h", "--help"):
        sys.exit()
    elif o in ("-d", "--debug"):
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




# retrieve messages from source
current_time = calendar.timegm(time.gmtime())


# create a map between a source and a list of messages from the source
messages = {}
messagesToWrite = {}

for name in sources_and_sinks:
    messagesToWrite[name] = []
    messages[name] = []
    messages[name] = copy.deepcopy(sources_and_sinks[name].gather())
    pass

one_hour = 3600
six_hours = one_hour * 6

# find all messages within the last hour from one source that are not present in another
for source in messages:
    if debug:
        print "================================================================="
        print "===== SOURCE: %s" % (source)
        print "================================================================="
        pass

    for message in messages[source]:
        
        if message.reply:
            continue
        
        if message.direct:
            continue
        
        delta_time = math.fabs(message.date - current_time)
        
        if debug:
            print "============================================================="
            print "Message to assess for sharing:"
            print "    "+message.content
            print "     Timestamp (UNIX Epoch): %f [Age (s): %f]" % (message.date, delta_time )
            pass
        
        
        
        if (math.fabs(message.date - current_time))<one_hour:
    
            for other_source in messages:

                best_match_score = 0;
                best_match_text = "";
                found_match = False
                
                if other_source == source:
                    continue
                for other_message in messages[other_source] + messagesToWrite[other_source]:
                    if other_message.content == None:
                        continue

                    if math.fabs(other_message.date - current_time) > six_hours:
                        continue

                    #match_ratio = fuzz.QRatio(message.content, other_message.content, force_ascii=True)
                    match_ratio = fuzz.token_set_ratio(message.content, other_message.content, force_ascii=True)
                    if match_ratio >= best_match_score:
                        best_match_score = match_ratio
                        best_match_text = "   BEST MATCH ON %s: %f  ____ " % (other_source, match_ratio) + other_message.content
                        pass
                    if match_ratio > 80:
                        found_match = True
                        break
                    pass
                
                if debug:
                    print best_match_text
                    pass

                if not found_match:
                    if message.repost:
                        message.content = 'RT ' + message.content
                        pass
                    
                    messagesToWrite[other_source].append(message)
                    pass
                pass
            pass
        pass
    pass


if debug:
    print "The list of messages to write (targets and message objects):"
    print messagesToWrite
    pass

for sinkname in sources_and_sinks:

    logging.info("Writing to sink: %s", sinkname)
    
    message_archive_filename = home+"/.navierstokes/message_archive_"+sinkname+".txt"
    if not os.path.exists(message_archive_filename):
        open(message_archive_filename, 'w').close() 
        pass
    
    lock = FileLock(message_archive_filename)
    lock_try_count = 0
    max_lock_try_count = 6
    obtained_lock = False
    while (not lock.i_am_locking()) and lock_try_count <= max_lock_try_count:
        try:
            lock.acquire(timeout=10)
        except LockTimeout:
            lock_try_count += 1
            logging.info("Lock acquisition: %s", "Will try again to acquire a file lock on the message archive. (Try count = %d)" % (lock_try_count))
            pass

        if lock.i_am_locking():
            obtained_lock = True
            break

        elif lock_try_count == max_lock_try_count-1:
            # let's see if the lock needs cleaning
            lock_creation_time = os.path.getctime(message_archive_filename+".lock")
            lock_creation_delta = math.fabs(current_time - lock_creation_time)
            logging.info("Lock file creation time: %s" , "%f seconds ago" % (lock_creation_delta))
            if lock_creation_delta > 600:
                os.remove(message_archive_filename+".lock")
                pass
            pass

        elif lock_try_count == max_lock_try_count:
            logging.info("Unable to resolve lock problem. %s", "Exiting")
            break
            pass
        
        pass

    if not obtained_lock:
        logging.info("Failed to acquire lock; %s", "moving onto another target")
        continue
    
    

    if debug:
        print "File lock on %s accomplished..." % (message_archive_filename)
        pass
    
    message_archive_file = open(message_archive_filename, 'a+')
    
    # generate md5sum from message 
    if debug:
        print "Checking MD5 sum of this message against that of messages already written..."
        pass

    messagesToActuallyWrite = []

    if debug:
        print messagesToWrite[sinkname]
        pass

    for message in messagesToWrite[sinkname]:
        try:
            message_md5sum = hashlib.md5(message.content).hexdigest()
        except UnicodeEncodeError:
            message_md5sum = hashlib.md5(message.content.encode('utf-8')).hexdigest()
            pass

        # print message_md5sum
        # see if this message was already written to this sink
        message_already_written = False
        for existing_message_md5sum in message_archive_file:
            # print "   " + existing_message_md5sum
            if existing_message_md5sum == message_md5sum:
                message_already_written = True
                break
            pass
        
        if not message_already_written:
            if debug:
                print "   According to the MD5 sum check, this message is new..."
                pass
            messagesToActuallyWrite.append( message )
            if not debug:
                message_archive_file.write( message_md5sum + "\n" )
                pass
            pass
        else:
            if debug:
                print "   This MD5 sum is not unique; the message will not be written again."
                pass
            pass
        pass
    
    if debug:
        print messagesToActuallyWrite
    else:
        sources_and_sinks[sinkname].write( messagesToActuallyWrite )
        pass
    message_archive_file.close()
    
    lock.release()
    
    pass
