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
import time
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

        whoami = commands.getoutput('t whoami | grep "Screen name"')

        matches = re.search('.*Screen name.*?@(.*)$', whoami, re.DOTALL)
        username = "";
        if matches:
            username = matches.group(1)
            username = username.rstrip('\n')
        else:
            return []
        


        text = commands.getoutput('t timeline -c @%s' % (username))

        for line in text.split('\n'):
            # 437607107773206528,2014-02-23 15:17:19 +0000,drsekula,message text
            matches = re.search('(.*?),(.*?),(.*?),(.*)', line, re.DOTALL)

            if matches:
                if matches.group(1) == "ID":
                    continue
                message_text = matches.group(4)
                message = Message()
                message.id = int(matches.group(1))
                message_time_text = time.strptime(matches.group(2), "%Y-%m-%d %H:%M:%S +0000")
                message.date = calendar.timegm(message_time_text)
                message.source = "Twitter"
                message.SetContent(message_text)
                message.author = username
                message.reply = True if (message_text[0] == "@" or message_text[0:2] == ".@") else False
                message.direct = True if (message_text[0] == "@") else False
                message.public = 1
                message.repost = True if (message_text[0:2] == "RT") else False

                self.messages.append( message )

                pass
            pass
        
        


        self.messages = sorted(self.messages, key=lambda msg: msg.date, reverse=False)

        if self.debug:
            print "********************** Twitter Handler **********************\n"
            print "Here are the messages I gathered from the Twitter account:\n"
            for message in self.messages:
                message.Print()
                pass

            pass

        return self.messages
    

    def write(self, messages):
        for message in messages:

            if self.sharelevel == "Public" and not message.public:
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

