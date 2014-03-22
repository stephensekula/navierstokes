"""
FacebookTools.py
Author: Stephen J. Sekula
Created: Mar. 13, 2013

* FacebookHandler:
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
import unicodedata

from MessageObj import Message


class FacebookHandler(SocialHandler):
    """ a class to read and post to a Facebook feed """
    def __init__(self,username="",sharelevel="public",album="latest"):
        self.username = username
        self.sharelevel = sharelevel
        self.album = album
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

        self.messages = []

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
                    msg.source = "Facebook"

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

        # handle images - they don't show up in the fstream
        messages_text = commands.getoutput('fbcmd opics "%s"' % (self.username))

        in_message = False
        msg = Message()

        photo_pid_column = -1
        text_column = -1

        first_line_pattern = re.compile('^%s\s+([0-9]+_[0-9]+)(\s.*)' % (self.username))

        for line in messages_text.split('\n'):

            line = str(line)
            #line = unicode(line).encode('unicode_escape')
            
            #try:
            #    line = unicodedata.normalize('NFKD', line).encode('ascii','ignore')
            #except TypeError:
            #    line = line
            #    pass

            if line.find("NAME") != 1 and line.find("PID") != -1 and line.find("CAPTION") != -1:
                continue

            # new messages begin with a PID. To determine the column containing
            # the PID, we need to do some math.
        
            # Stephen Sekula  100000196682628_1073741900  Tracking down bug
            first_line_pattern_match = first_line_pattern.search(line)
            if first_line_pattern_match != None and photo_pid_column == -1:
                # we found the key line of the output - find the column where the PID starts
                pid = first_line_pattern_match.group(1)
                photo_pid_column = line.find(pid)
                pass

            pid_pattern = re.search('^.*?  ([0-9]+_[0-9]+)\s.*', line, re.DOTALL)
            pid_match = re.search("[0-9]", line[photo_pid_column],re.DOTALL)
            if pid_match:
                pid = pid_pattern.group(1)
                if not in_message:
                    # we found the first line of a photo message.
                    msg = Message()
                    msg.source = "Facebook"
                    
                    # we need to find the start of the actual message
                    text_column = photo_pid_column+len(pid)
                    msg.content = msg.content + line[text_column:].lstrip()
                    
                    in_message = True
                    pass
                else:
                    # we found the start of the next message. close the last one
                    
                    # check if the message has any content before saving
                    if re.search(".*[A-Za-z0-9].*",msg.content,re.DOTALL) != None:
                        self.messages.append(msg)
                        pass

                    msg = Message()
                    msg.source = "Facebook"


                    msg.content = str(msg.content) + line[text_column:].lstrip()
                    in_message = True
                    pass
                pass
            else:
                # we are still in the last message - keep doing things

                msg.content = str(msg.content + " " + line[text_column:].lstrip())

                pass
            pass

        self.messages = sorted(self.messages, key=lambda msg: msg.date, reverse=False)

        if self.debug:
            print "********************** Facebook Handler **********************\n"
            print "Here are the messages I gathered from the Facebook server:\n"
            for message in self.messages:
                message.Print()
                pass
            print "**************************************************************\n"
        
        return self.messages
    

    def write(self, messages):
        if not self.active:
            self.msg(0,"Facebook handler not active; no messages will be posted")
            return

        self.msg(0,"Share level is: %s" % (self.sharelevel))

        write_count = 0

        for message in messages:

            do_write = False
            
            text = self.HTMLConvert(message.content)
            text = text.replace('"','\\"')


            if self.sharelevel == "All":
                do_write = True
            elif self.sharelevel.find("Public") != -1 and message.public == 1:
                self.msg(0,"Unable to share message, as it is not public.")
                do_write = True
                pass
            else:
                self.msg(0,"Unable to share message for unknown reasons.")
                pass

            if not do_write:
                continue
            
            success = False
            self.msg(0,"writing to Facebook")
            if len(message.attachments) > 0:
                if self.debug:
                    self.msg(0,"   Posting a photo.")
                    pass

                for attachment in message.attachments:
                    command = "fbcmd ADDPIC %s \"%s\" \"%s\"" % (attachment, self.album, text)
                    if self.debug:
                        self.msg(0, "   " + command)
                        pass
                    results = commands.getoutput(command)
                    pass
                pass
            else:
                command = "fbcmd STATUS \"%s\"" % (text)
                if self.debug:
                    self.msg(0, "   " + command)
                    pass
                results = commands.getoutput(command)
                pass

            write_count += 1
            pass

        self.msg(0,"Wrote %d messages" % write_count)
        return

