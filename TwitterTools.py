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
    def __init__(self):
        self.messages = []
        self.debug = False
        pass


                        

    def gather(self):

        self.messages = []

        self.messages = sorted(self.messages, key=lambda msg: msg.date, reverse=False)

        if self.debug:
            print "********************** Twitter Handler **********************\n"
            print "Here are the messages I gathered from the Twitter account:\n"
            for message in self.messages:
                message.Print()
                pass

        return self.messages
    

    def write(self, messages):
        for message in messages:
        
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
            if self.debug:
                self.msg(level=0,text=command)
                pass

            results = commands.getoutput(command)

            pass

        self.msg(0,"Wrote %d messages" % len(messages))
        return

