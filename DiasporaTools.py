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
import calendar
import datetime
import commands
import codecs

class DiasporaHandler(SocialHandler):
    def __init__(self, webfinger, password, aspect="public", sharelevel="Public"):
        SocialHandler.__init__(self)
        self.webfinger = webfinger
        self.password = password
        self.usermap = {}
        self.aspect = aspect
        self.sharelevel = sharelevel

        pass



    def ParseStream(self, text=""):
        # messages begin with a line that contains "POST-ID:" and end
        # with a line that contains COMMENTS:

        in_message = False

        lines = text.split('\n')
        
        msg = Message()

        for line in lines:
            if not in_message:
                if line.find("POST-ID:") != -1:
                    in_message = True
                    # create a new message object
                    msg = Message()
                    msg.source = "Diaspora"
                    # parse the timestamp and the post ID
                    matches = re.search('(2.*Z) POST-ID: ([0-9]+).*', line, re.DOTALL)
                    if matches:
                        msg.date = calendar.timegm(datetime.datetime.strptime(matches.group(1),"%Y-%m-%dT%H:%M:%SZ").timetuple())
                        msg.id = int(matches.group(2))
                        msg.link = '%s/posts/%d' % (self.webfinger.split('@')[1],msg.id)
                        pass
                    pass
                pass
            else:
                if line.find("COMMENTS") != -1:
                    in_message = False

                    #msg.SetContent( msg.content.replace('arx-iv','arxiv') )
                    #msg.SetContent( msg.content.replace('arX-iv','arXiv') )

                    self.append_message(msg)
                    pass
                elif line.find("POST-ID:") != -1:
                    # we are in a message, but this is a reshare. Handle the first line
                    # carefully!
                    original_author_match = re.search('<(.*)> on .*', line, re.DOTALL)
                    if original_author_match:
                        # found the original author. Mark this message as a repost
                        # and credit the original author
                        original_author_name = original_author_match.group(1)
                        msg.SetContent(msg.content + "From %s on Diaspora: " % (original_author_name))
                        msg.repost = 1
                        pass

                else:
                    # we are in a message - get a line and add to content.
                    # watch for hyphenated line-break words
                    line = line.rstrip('\n')

                    if len(msg.content)==0 and len(line) > 0 and line[0] == '@':
                        msg.direct = 1

                    if not re.search('.*[a-zA-Z]-$', line):
                        line = line + " "
                        pass
                    msg.SetContent(msg.content + line)
                pass

            pass
        return
        

    def gather(self):

        self.messages = []

        response = os.system('cliaspora status')
        if response == 256:
            password = self.password.replace(' ','\ ')
            os.system('cliaspora session new %s "%s"' % (self.webfinger, password))
            pass
        
        text = commands.getoutput('cliaspora show mystream | sed -e \'s/\.br/\.nf \.nh/\' | preconv | groff -Tascii')
        
        self.ParseStream(text)

        self.messages = sorted(self.messages, key=lambda msg: msg.date, reverse=False)

        if self.debug:
            print "********************** Diaspora Handler **********************\n"
            print "Here are the messages I gathered from the Diaspora server:\n"
            for message in self.messages:
                print message.Printable()
                pass

        return self.messages

    
    def write(self, messages=[]):
        
        successful_id_list = []

        for message in messages:

            self.msg(0,"writing to Diaspora")

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

            notice_text = message.content

            # user mapping
            notice_text = self.map_users(notice_text)

            notice_file = codecs.open('/tmp/diaspora','w',encoding='utf-8')
            notice_file.write(self.texthandler(notice_text))
            notice_file.close()


            response = os.system('cliaspora status')
            if response == 256:
                # session expired - renew it
                print "Session is expired - creating a new one..."
                #password = self.password.replace(' ','\ ')
                os.system('cliaspora session new %s \'%s\'' % (self.webfinger, self.password))
                pass
            
            aspect = self.aspect
            if message.public:
                aspect = "public"
                pass

            if len(message.attachments) > 0:
                for attachment in message.attachments:
                    # to post an image, first upload it then comment on it.
                    
                    post_succeeded = 0
                    post_tries = 0
                    
                    target_image_width=400

                    while post_succeeded == 0 and post_tries < 5:

                        post_response = self.texthandler("")

                        if post_tries != 0:
                            commands.getoutput('convert -scale %dx %s %s.small.png' % (target_image_width,attachment,attachment))
                            post_response = commands.getoutput('echo "%s" | cliaspora -m upload "%s" %s.small.png' % (notice_text,aspect,attachment))
                            target_image_width = target_image_width - 50
                        else:
                            post_response = commands.getoutput('echo "%s" | cliaspora -m upload "%s" %s' % (notice_text,aspect,attachment))
                            pass

                        if post_response.find("Failed") != -1:
                            post_succeeded = 0
                        else:
                            post_succeeded = 1
                            pass
                        
                        if post_succeeded:
                            successful_id_list.append( message.id )

                        post_tries = post_tries + 1

                        pass

                    pass
                pass
            else:
                os.system('cat /tmp/diaspora | cliaspora post "%s"' % (aspect))
                successful_id_list.append( message.id )
                pass
            pass

        self.msg(0, "Wrote %d messages." % (len(messages)))
        return successful_id_list
    
