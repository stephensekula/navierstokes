"""
TwitterTools.py
Author: Stephen J. Sekula
Created: Apr. 27, 2014

* TwitterHandler:
Inherits from: SocialHandler
Purpose: to gather messages from a Twitter account, and write messages to
the same account. It uses the RubyGem "t" and the Twitter API to do all of this.
"""

from SocialHandler import *
import xml.dom.minidom
import sys

import subprocess
import os
import re
import datetime
import calendar
import commands

import URLShortener

from MessageObj import Message


class TwitterHandler(SocialHandler):
    """ a class to read and post to a GNU Social feed """
    def __init__(self,sharelevel="Public"):
        SocialHandler.__init__(self)
        self.sharelevel = sharelevel
        self.configfile = ""
        pass


                        

    def gather(self):

        self.messages = []

        self.msg(0, self.texthandler("Gathering messages."))

        configstring = ""
        if self.configfile != "":
            configstring = '-P %s' % (self.configfile)
            pass

        whoami = self.texthandler(commands.getoutput('t whoami %s | grep "Screen name"' % (configstring)))

        matches = re.search('.*Screen name.*?@(.*)$', whoami, re.DOTALL)
        username = self.texthandler("");
        if matches:
            username = self.texthandler(matches.group(1))
            username = username.rstrip('\n')
        else:
            return []
        


        text = self.texthandler(commands.getoutput('t timeline %s -c @%s' % (configstring,username)))

        message = Message()

        line = self.texthandler("")

        for line in text.split('\n'):
            # 437607107773206528,2014-02-23 15:17:19 +0000,drsekula,message text
            matches = re.search('(.*?),(.*?),(.*?),(.*)', line, re.DOTALL)

            if matches:
                
                # the first line of t output is just header information
                if matches.group(1) == "ID":
                    continue


                message_text = self.texthandler(matches.group(4))

                # t does funny things with quotes in messages that are not RTs.
                message_text = message_text.lstrip("\"")
                message_text = message_text.rstrip("\"")
                message_text = message_text.replace("\"\"","\"")

                message = Message()
                message.id = int(matches.group(1))
                message_time_text = datetime.datetime.strptime(matches.group(2), "%Y-%m-%d %H:%M:%S +0000")
                message.date = calendar.timegm(message_time_text.timetuple())
                message.source = "Twitter"
                message.SetContent(self.TextToHtml(message_text))
                message.author = username
                message.reply = True if (message_text[0] == "@" or message_text[1] == "@") else False
                message.direct = True if (message_text[0] == "@" or message_text[1] == "@") else False
                if message.reply or message.direct:
                    message.public = False
                else:
                    message.public = True
                    pass
                message.repost = True if (message_text.find("RT ") != -1) else False

                if message.repost:
                    message.SetContent( self.texthandler("From <a href=\"https://twitter.com/%s\">Twitter</a>: " % (username)) + message.content )
                    pass


                self.messages.append( message )

                pass

            else:
                # this might just be another line in a multi-line message in Twitter
                message.content += self.texthandler("\n") + line;
                pass

            pass
        
        


        self.messages = sorted(self.messages, key=lambda msg: msg.date, reverse=False)

        if self.debug:
            print "********************** Twitter Handler **********************\n"
            print "Here are the messages I gathered from the Twitter account:\n"
            for message in self.messages:
                print message.Printable()
                pass

            pass


        return self.messages
    

    def write(self, messages):

        successful_id_list = []

        configstring = ""
        if self.configfile != "":
            configstring = '-c %s' % (self.configfile)
            pass

        for message in messages:

            do_write = False
            if self.sharelevel == "All":
                do_write = True
            elif self.sharelevel.find("Public") != -1 and message.public == 1:
                do_write = True
                pass
            else:
                do_write = False
                pass

            if not do_write:
                self.msg(0,message.content)
                self.msg(0,"Unable to share above message based on sharelevel settings.")
                continue

       
            success = False
            self.msg(0,"Writing to Twitter")

            # if message is too long, chop it and add URL
            #message_text = copy.deepcopy(message.content)
            #if len(message_text) > 140:
            #    message_text = message_text[:97] + "..."
            #    message_text += URLShortener.URLShort

            message_text = self.texthandler(copy.deepcopy(message.content))
            if len(message_text) <= 140:
                tweet = message.content
                tweet = tweet.replace('\n',' ')

                command = self.texthandler("t update %s '%s'" % (configstring,tweet))

                if len(message.attachments) > 0:
                    command += self.texthandler(" -f %s" % (message.attachments[0]))
                    pass

                if self.debug:
                    self.msg(level=0,text=command)
                    pass

                try:
                    results = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
                    if results.find('Tweet posted') != -1:
                        successful_id_list.append( message.id )
                except subprocess.CalledProcessError:
                    continue

                tries = 0

                while results.find('Tweet posted') == -1 and tries < 5:
                    self.msg(1,"Posting to twitter failed - trying again...")
                    try:
                        results = subprocess.check_output(command, stderr=subprocess.STDOUT,shell=True)
                        if results.find('Tweet posted') != -1:
                            successful_id_list.append( message.id )
                    except subprocess.CalledProcessError:
                        pass
                    tries = tries + 1
                    pass
                pass
            pass

        self.msg(0,"Wrote %d messages" % len(messages))
        return successful_id_list

