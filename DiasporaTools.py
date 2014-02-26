"""
DiasporaTools.py
Author: Stephen J. Sekula
Created: Dec. 23, 2013

* DisaporaHandler:
Inherits from: SocialHandler
Purpose: to gather messages from a Diaspora instance, and write messages to
the same instance. It uses an external tool to do all of this, currently
"cliaspora" (version 0.1.7 is currently employed) - 
http://freeshell.de/~mk/projects/cliaspora.html
"""

from SocialHandler import *
from MessageObj import Message

import subprocess
import os
import re
import time
import commands
import codecs

class DiasporaHandler(SocialHandler):
    def __init__(self, webfinger, password):
        self.webfinger = webfinger
        self.password = password
        self.usermap = {}
        self.messages = []

        self.debug = False

        pass



    def ParseStream(self, text=""):
        # messages begin with a line that contains "POST-ID:" and end
        # with a line that contains COMMENTS:

        in_message = False

        lines = text.split('\n')
        
        messages = []

        msg = Message()

        for line in lines:
            if not in_message:
                if line.find("POST-ID:") != -1:
                    in_message = True
                    # create a new message object
                    msg = Message()
                    # parse the timestamp and the post ID
                    matches = re.search('(2.*Z) POST-ID: ([0-9]+).*', line, re.DOTALL)
                    if matches:
                        msg.date = time.mktime(time.strptime(matches.group(1),"%Y-%m-%dT%H:%M:%SZ"))
                        msg.id = int(matches.group(2))
                        pass
                    pass
                pass
            else:
                if line.find("COMMENTS:") != -1:
                    in_message = False

                    msg.content = msg.content.replace('arx-iv','arxiv')
                    msg.content = msg.content.replace('arX-iv','arXiv')

                    if self.debug:
                        msg.Print()
                        pass
                    messages.append(msg)
                    pass
                else:
                    # we are in a message - get a line and add to content.
                    # watch for hyphenated line-break words
                    line = line.rstrip('\n')
                    if not re.search('.*[a-zA-Z]-$', line):
                        line = line + " "
                        pass
                    msg.content += line
                pass

            pass



        return messages
        

    def gather(self):

        response = os.system('cliaspora status')
        if response == 256:
            password = self.password.replace(' ','\ ')
            os.system('cliaspora session new %s "%s"' % (self.webfinger, password))
            pass
        
        text = commands.getoutput('cliaspora show mystream | preconv | groff -Tascii')
        
        self.messages = self.ParseStream(text)

        self.messages = sorted(self.messages, key=lambda msg: msg.date, reverse=False)

        return self.messages

    
    def write(self, messages=[]):
        
        for message in messages:
            notice_text = message.content

            # user mapping
            notice_text = self.map_users(notice_text)

            notice_file = open('/tmp/diaspora','w')
            notice_file.write(unicode(notice_text).encode("utf-8"))
            notice_file.close()


            response = os.system('cliaspora status')
            if response == 256:
                # session expired - renew it
                print "Session is expired - creating a new one..."
                #password = self.password.replace(' ','\ ')
                os.system('cliaspora session new %s \'%s\'' % (self.webfinger, self.password))
                pass
            
            if len(message.attachments) > 0:
                for attachment in message.attachments:
                    # to post an image, first upload it then comment on it.
                    os.system('cliaspora upload public %s' % (attachment))
                    # get the POST-ID of this image
                    post_id = commands.getoutput("cliaspora show activity | grep \"POST-ID\" | head -1")
                    post_id = post_id.replace('\n','')
                    post_id = re.search('.*POST-ID: ([0-9]*)\.*',post_id).group(1)
                    os.system('cat /tmp/diaspora | cliaspora comment %s' % (post_id))
                    pass
                pass
            else:
                os.system('cat /tmp/diaspora | cliaspora post public')
                pass
            pass

        self.msg(0, "Wrote %d messages." % (len(messages)))
        return
    
