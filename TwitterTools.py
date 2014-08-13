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

from MessageObj import Message


class TwitterHandler(SocialHandler):
    """ a class to read and post to a GNU Social feed """
    def __init__(self,sharelevel="Public"):
        self.messages = []
        self.debug = False
        self.sharelevel = sharelevel
        pass


                        

    def gather(self):

        self.messages = []

        self.msg(0, "Gathering messages.")

        whoami = commands.getoutput('t whoami | grep "Screen name"')

        matches = re.search('.*Screen name.*?@(.*)$', whoami, re.DOTALL)
        username = "";
        if matches:
            username = matches.group(1)
            username = username.rstrip('\n')
        else:
            return []
        


        text = commands.getoutput('t timeline -c @%s' % (username))

        message = Message()

        for line in text.split('\n'):
            # 437607107773206528,2014-02-23 15:17:19 +0000,drsekula,message text
            matches = re.search('(.*?),(.*?),(.*?),(.*)', line, re.DOTALL)

            if matches:
                
                # the first line of t output is just header information
                if matches.group(1) == "ID":
                    continue


                message_text = matches.group(4)
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
                    message.SetContent( "From <a href=\"https://twitter.com/%s\">Twitter</a>: " % (username) + message.content )
                    pass

                self.messages.append( message )

                pass

            else:
                # this might just be another line in a multi-line message in Twitter
                message.content += "\n" + line;

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
        for message in messages:

            do_write = False
            if self.sharelevel == "All":
                do_write = True
            elif self.sharelevel.find("Public") != -1 and message.public == 1:
                do_write = True
                pass
            else:
                self.msg(0,message.content)
                self.msg(0,"Unable to share message based on sharelevel settings.")
                do_write = False
                pass

            if not do_write:
                continue
        
            success = False
            self.msg(0,"writing to Twitter")

            text = self.HTMLConvert(message.content)

            text = text.lstrip(' ')
            text = text.rstrip('\n')
            text = text.replace('"','\\"')

            if self.debug:
                print "Message text after HTML -> ascii conversion:"
                print text
                print "---- END OF LINE ----"
                pass


            command = "t update \"%s\"" % (text)

            if len(message.attachments) > 0:
                command += " -f %s" % (message.attachments[0])
                pass

            if self.debug:
                self.msg(level=0,text=command)
                pass

            results = commands.getoutput(command)

            pass

        self.msg(0,"Wrote %d messages" % len(messages))
        return

