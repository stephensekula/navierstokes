"""
FacebookTools.py
Author: Stephen J. Sekula
Created: Mar. 13, 2013

* GNUSocialHandler:
Inherits from: SocialHandler
Purpose: to gather messages from a Facebook instance, and write messages to
the same instance. It uses FBCMD to do its work.
"""

from SocialHandler import *
import sys

import subprocess
import os
import re
import time
import calendar
import commands

from MessageObj import Message


class FacebookHandler(SocialHandler):
    """ a class to read and post to a GNU Social feed """
    def __init__(self,username="",sharelevel=""):
        self.username = username
        self.sharelevel = sharelevel
        self.messages = []
        self.debug = False

        
        # check that fbcmd is installed
        self.active = True
        if self.which('fbcmd') == None:
            self.msg(0,"fbcmd not installed; Facebook handler will be inactive")
            self.active = False
            pass

        pass

    def gather(self):
        if not self.active:
            return []

        messages_text = commands.getoutput('fbcmd fstream "%s" 25' % (self.username))

        in_message = False
        msg = Message()

        for line in messages_text.split('\n'):

            # new messages begin with [number].

            if not in_message:
                matches = (re.search('^\[[0-9]+\].*', line, re.DOTALL) != None)
                matches = matches and (line[0:len(self.username)+10].find(self.username) != -1)

                if matches:
                    in_message = True
                    
                    msg = Message()

                    # we need to find the start of the actual message
                    message_text_match = re.search('.*attach post  (.*)',line,re.DOTALL)
                    if message_text_match == None:
                        message_text_match = re.search('.*link post  (.*)',line,re.DOTALL)
                        pass
                    if message_text_match == None:
                        message_text_match = re.search('.*photo post  (.*)',line,re.DOTALL)
                        pass
                    if message_text_match != None:
                        msg.content =  message_text_match.group(1)
                    else:
                        print "PROBLEM:"
                        print line
                        pass
                    pass
            else:
                hit_likes_or_comments = (line.find(':likes') != -1) or (line.find(':comment') != -1)
                hit_next  = (re.search('^\[[0-9]+\].*', line, re.DOTALL) != None)
                if hit_likes_or_comments:
                    # we have finished the message content. Close it.
                    in_message = False
                    self.messages.append( msg )
                    pass
                elif hit_next:
                    # we are in the next message - close the last and start a new one
                    in_message = False
                    self.messages.append( msg )
                    pass
                else:
                    # we are still in the last message - keep doing things
                    message_text_match = re.search('.*?(\S.*)',line, re.DOTALL)
                    if message_text_match != None:
                        msg.content = msg.content + " " + message_text_match.group(1)
                        pass
                    
                pass
            pass

        if self.debug:
            print "********************** Facebook Handler **********************\n"
            print "Here are the messages I gathered from the Facebook server:\n"
            for message in self.messages:
                message.Print()
                pass
        
        return self.messages
    

    def write(self, messages):
        if not self.active:
            self.msg(0,"Facebook handler not active; no messages will be posted")
            return

        self.msg(0,"   Share level is: %s" % (self.sharelevel))

        write_count = 0

        for message in messages:

            do_write = False
            
            text = self.HTMLConvert(message.content)

            if self.sharelevel == "All":
                do_write = True
            elif self.sharelevel.find("Public") != -1 and message.public == 1:
                self.msg(0,"   Unable to share message, as it is not public.")
                do_write = True
                pass
            else:
                self.msg(0,"   Unable to share message for unknown reasons.")
                pass

            if not do_write:
                continue
            
            command = "fbcmd STATUS \'%s\'" % (text)

            success = False
            self.msg(0,"writing to Facebook")
            results = commands.getoutput(command)
            write_count += 1
            pass

        self.msg(0,"Wrote %d messages" % write_count)
        return

