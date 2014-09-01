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
import unicodedata
from sets import Set

from os.path import expanduser
from lockfile import FileLock,LockTimeout

import requests
from requests_oauthlib import OAuth1

import GNUSocialTools
import PumpTools
import DiasporaTools
import FacebookTools
import TwitterTools
import RSSTools
import URLShortener

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

# Check if a PID file already exists
path_to_pidfile = home + '/.navierstokes/navierstokes.pid'
pid_is_running = False
if os.path.exists( path_to_pidfile ):
    # see if this PID is _actually_ running
    pid = int(open(path_to_pidfile).read())

    try:
        os.kill(pid, 0)
    except OSError:
        pid_is_running = False
    else:
        pid_is_running = True
        pass

    if pid_is_running:
        logging.info("This program is already running, and should not be run twice.")
        sys.exit()
    else:
        os.remove(path_to_pidfile)
        logging.info("An old PID file was present, but the program is not running.")
        logging.info("Removing the old PID file and running the program anew.")
        open(path_to_pidfile, 'w').write(str(os.getpid()))
        pass
else:
    open(path_to_pidfile, 'w').write(str(os.getpid()))
    pass

    

# Parse command line options
try:
    opts, args = getopt.getopt(sys.argv[1:], "dhi:o:", ["debug","help", "input=", "output="])
except getopt.GetoptError as err:
    # print help information and exit:
    print str(err) # will print something like "option -a not recognized"
    os.remove(path_to_pidfile)
    sys.exit(2)
    pass
output = None
input = None
verbose = False
debug = False
fuzzy = False

for o, a in opts:
    if o in ("-h", "--help"):
        os.remove(path_to_pidfile)
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
urlShorteningConfig = {}

# Use the config file to setup the sources and sinks
config = ConfigParser.ConfigParser()
config.read(home+'/.navierstokes/navierstokes.cfg')
    

for section in config.sections():
    logging.info("Configuring a handler named %s", section)
    if config.get(section, "type") == "rss":
        sources_and_sinks[section] = RSSTools.RSSHandler(feed_url=config.get(section, "feed_url"))

        pass
    if config.get(section, "type") == "gnusocial":
        sources_and_sinks[section] = GNUSocialTools.GNUSocialHandler(site=config.get(section, "site"), \
                                                                         username=config.get(section, "username"), \
                                                                         sharelevel=config.get(section,"sharelevel"), \
                                                                         password=config.get(section, "password"))


        pass
    elif config.get(section, "type") == "pump.io":
        client_credentials = config.get(section, "client_credentials").split(',')
        client_tokens=config.get(section, "client_tokens").split(',')

        sources_and_sinks[section] = PumpTools.PumpHandler(webfinger=config.get(section, "webfinger"), \
                                                               credentials=client_credentials, \
                                                               tokens=client_tokens, \
                                                               sharelevel=config.get(section,"sharelevel"))
        pass
    elif config.get(section, "type") == "diaspora":
        sources_and_sinks[section] = DiasporaTools.DiasporaHandler(webfinger=config.get(section, "webfinger"), \
                                                                       password=config.get(section, "password"), \
                                                                       aspect=config.get(section,"aspect"),
                                                                       sharelevel=config.get(section,"sharelevel"))
        pass
    elif config.get(section, "type") == "facebook":
        sources_and_sinks[section] = FacebookTools.FacebookHandler(album=config.get(section, "album"), \
                                                                   sharelevel=config.get(section, "sharelevel"))
        pass
    elif config.get(section, "type") == "twitter":
        sources_and_sinks[section] = TwitterTools.TwitterHandler(sharelevel=config.get(section, "sharelevel"))
        pass
    elif section.lower() == 'urlshortening':
		try: 
			urlShorteningConfig['service'] = config.get(section, "service")
			urlShorteningConfig['url'] = config.get(section, "serviceURL")
			urlShorteningConfig['key'] = config.get(section, "serviceKey")
        except:
			#default to ur1.ca
			urlShorteningConfig['service'] = 'ur1'
			urlShorteningConfig['url'] = 'http://ur1.ca'
			urlShorteningConfig['key'] = False
        continue
    pass


    do_url_shortening = False
    try:
        do_url_shortening = True if (config.get(section, "shortenurls") == "True") else False        
    except ConfigParser.NoOptionError:
        do_url_shortening = True        
        pass
    sources_and_sinks[section].do_url_shortening = do_url_shortening

    max_message_age = 3600
    try:
        max_message_age = config.get(section, "max_message_age")
    except ConfigParser.NoOptionError:
        max_message_age = 3600
        pass
    sources_and_sinks[section].max_message_age = max_message_age


if debug == True:
    for handler in sources_and_sinks:
        logging.info("Setting %s to debug mode", handler)
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
    
    if sources_and_sinks[name].do_url_shortening:
		sources_and_sinks[name].urlShorteningConfig = urlShorteningConfig
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

        if message.content == None:
            continue
        
        delta_time = math.fabs(message.date - current_time)
        
        if debug:
            print "============================================================="
            print "Message to assess for sharing:"
            print "    "+message.content
            print "     Timestamp (UNIX Epoch): %f [Age (s): %f]" % (message.date, delta_time )
            pass
        
        max_message_age = float(sources_and_sinks[source].max_message_age)
        
        if (math.fabs(message.date - current_time))<max_message_age:
    
            for other_source in messages:

                best_match_score = 0;
                best_match_text = "";
                found_match = False
                
                if other_source == source:
                    continue

                # see if this message is already present in the messages to be written
                # to the other source. If so, see if we should replace that one
                # with this one, which may be better (e.g. have attachments, etc.)
                message_already_written_index = -1
                for other_message in messagesToWrite[other_source]:
                    message_already_written_index += 1
                    if other_message.content == None:
                        continue

                    match_ratio = fuzz.token_set_ratio(message.content, other_message.content, force_ascii=True)
                    if match_ratio >= best_match_score:
                        best_match_score = match_ratio
                        best_match_text = "   BEST MATCH ON %s: %f  ____ " % (other_source, match_ratio) + other_message.content
                        pass

                    if match_ratio > 80:
                        # check if this message is better quality than the one already scheduled to be 
                        # written
                        found_match = True
                        if other_message.source == "Diaspora":
                            # Cliaspora loses attachments. Maybe replace with this message.
                            if debug:
                                print "Replacing message from Disapora with message from %s" % (message.source)
                                pass

                            messagesToWrite[other_source][message_already_written_index] = copy.deepcopy(message)
                            pass
                        pass
                    pass

                if not found_match:
                    for other_message in messages[other_source] + messagesToWrite[other_source]:
                        if other_message.content == None:
                            continue

                        match_ratio = fuzz.token_set_ratio(message.content, other_message.content, force_ascii=True)
                        if match_ratio >= best_match_score:
                            best_match_score = match_ratio
                            best_match_text = "   BEST MATCH ON %s: %f  ____ " % (other_source, match_ratio) + other_message.content
                            pass
                        if match_ratio > 80:
                            found_match = True
                            break
                        pass
                    pass

                
                if debug:
                    print best_match_text
                    pass

                if not found_match:
                    logging.info("Message to consider")
                    logging.info(message.content)
                    logging.info("  %s", best_match_text)
                    messagesToWrite[other_source].append(copy.deepcopy(message))
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
    
    
    # generate md5sum from message 
    if debug:
        print "Checking MD5 sum of this message against that of messages already written..."
        pass


    if debug:
        print messagesToWrite[sinkname]
        pass


    # Message modificaton - remove tracking links, remove HTML, etc. as appropriate
    for message in messagesToWrite[sinkname]:
        if debug:
            print "====================================================================="
            print " MESSAGE CLEANUP FOR %s " % (sinkname)
            print "====================================================================="
            
        found_urls = re.findall('(?:http[s]{0,1}://|www.)[^"\'<> ]+', message.content, re.MULTILINE)
        unique_urls = list(Set(found_urls))
        for url in unique_urls:
            new_url = URLShortener.ExpandShortURL(url)
            try:
                message.content = message.content.replace(url,new_url)
            except UnicodeDecodeError:
                url = url.encode('utf-8')
                new_url = new_url.encode('utf-8')
                message.content = message.content.replace(url,new_url)
                pass
            pass


        if type(sources_and_sinks[sinkname]) == TwitterTools.TwitterHandler or \
           type(sources_and_sinks[sinkname]) == GNUSocialTools.GNUSocialHandler or \
           type(sources_and_sinks[sinkname]) == FacebookTools.FacebookHandler:
            message.content = sources_and_sinks[sinkname].HTMLConvert(message.content)

        if type(sources_and_sinks[sinkname]) == TwitterTools.TwitterHandler or \
           type(sources_and_sinks[sinkname]) == GNUSocialTools.GNUSocialHandler:
            message.content = message.content.lstrip(' ')
            message.content = message.content.rstrip('\n')
            

        if type(sources_and_sinks[sinkname]) == TwitterTools.TwitterHandler or \
           type(sources_and_sinks[sinkname]) == FacebookTools.FacebookHandler:
            message.content = message.content.replace('"','\\"')
            

        if sources_and_sinks[sinkname].do_url_shortening:
            message.content = sources_and_sinks[sinkname].ShortenURLs(message.content)
            pass
            
        try:
            message.content = message.content.encode('utf-8')
        except UnicodeDecodeError:
            message.content = message.content.decode('iso-8859-1') 
            pass


        if type(sources_and_sinks[sinkname]) == FacebookTools.FacebookHandler:
            # fbcmd just cannot handle unicode...
            message.content = unicodedata.normalize('NFKD', unicode(message.content)).encode('ascii','ignore')

        if debug:
            print "Message text after cleanup:"
            print message.content
            print "------------------------------- END OF LINE -------------------------------"
            pass

        pass

    messagesToActuallyWrite = []


    for message in messagesToWrite[sinkname]:
        try:
            message_md5sum = hashlib.md5(message.content).hexdigest()
        except UnicodeEncodeError:
            message_md5sum = hashlib.md5(message.content.encode('utf-8')).hexdigest()
            pass

        # print message_md5sum
        # see if this message was already written to this sink
        message_already_written = False
        message_archive_file = open(message_archive_filename, 'r')
        for existing_message_md5sum in message_archive_file:
            existing_message_md5sum = existing_message_md5sum.rstrip('\n')
            # print "   " + existing_message_md5sum
            if existing_message_md5sum == message_md5sum:
                message_already_written = True
                break
            pass
        message_archive_file.close()
        

        if message_already_written:
            if debug:
                print "   This MD5 sum is not unique; the message will not be written again."
                pass
            pass
        else:
            if debug:
                print "   According to the MD5 sum check, this message is new..."
                pass
            
            messagesToActuallyWrite.append( copy.deepcopy(message) )
            if not debug:
                message_archive_file = open(message_archive_filename, 'a')
                message_archive_file.write( message_md5sum + "\n" )
                message_archive_file.close()
                pass
            pass
        pass
    
    if debug:
        for message in messagesToActuallyWrite:
            print message.Printable()
            pass
    else:
        for message in messagesToActuallyWrite:
            logging.info("New message to write:")
            print message.Printable()
            pass

        sources_and_sinks[sinkname].write( messagesToActuallyWrite )
        pass
    
    lock.release()
    
    pass

# We are done. Remove the PID file
os.remove(path_to_pidfile)
