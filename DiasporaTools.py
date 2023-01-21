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
import diaspy
import json
import html2text
import shutil
import time
from bs4 import BeautifulSoup


class DiasporaHandler(SocialHandler):
    def __init__(self, webfinger, guid, password, aspect="public", sharelevel="Public"):
        SocialHandler.__init__(self)
        self.webfinger = webfinger
        self.guid      = guid
        self.password = password
        self.usermap = {}
        self.aspect = aspect
        self.sharelevel = sharelevel

        pass



    def gather(self):

        self.messages = []

        connection = None
        try:
            connection = diaspy.connection.Connection(pod='https://%s' % (self.webfinger.split('@')[1]),username=self.webfinger.split('@')[0],password=self.password)
        except:
            return self.messages

        connection.login()
        stream = diaspy.streams.Activity(connection)
        #user   = diaspy.people.User(connection, guid=self.guid)

        for post in stream:
            msg = Message()
            msg.source = "Diaspora"
            msg.id = post['id']
            msg.link = '%s/posts/%d' % (self.webfinger.split('@')[1],msg.id)
            msg.author = post['author']['name']
            msg.title = post['title']
            msg.date   = calendar.timegm(datetime.datetime.strptime(post['created_at'],"%Y-%m-%dT%H:%M:%S.000Z").timetuple())
            msg.SetContent(msg.content + post.__str__())

            # harvest media from the post
            for medium in post['photos']:
                post_attachment = medium["sizes"]["large"]
                filename = post_attachment.split('/')[-1]
                if not os.path.exists('/tmp/%s' % (filename)):
                    os.system('curl --connect-timeout 60 -m 120 -s -o /tmp/%s %s' % ( filename, post_attachment ))
                    pass
                msg.attachments.append( '/tmp/%s' % (filename) )
                pass

            # determine the message type
            if post['post_type'] == "StatusMessage":
                msg.repost = 0
                msg.direct = 0
                if post['author']['guid'] != self.guid:
                    continue
                #if msg.author != user['name']:
                #    continue
            elif post['post_type'] == "Reshare":
                msg.repost = 1
                msg.direct = 0
                msg.SetContent(msg.content + "\n\n" + "Reshared from %s on Diaspora: " % (post.author()))
                pass
            else:
                continue

            if post['public'] == True:
                msg.public = 1
            else:
                msg.public = 0

            self.messages.append(msg)

        self.messages = sorted(self.messages, key=lambda msg: msg.date, reverse=False)

        if self.debug:
            print("********************** Diaspora Handler **********************\n")
            print("Here are the messages I gathered from the Diaspora server:\n")
            for message in self.messages:
                print(message.Printable())
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

            # create a connection to the pod and write
            connection = diaspy.connection.Connection(pod='https://%s' % (self.webfinger.split('@')[1]),username=self.webfinger.split('@')[0],password=self.password)
            connection.login()
            try:
                stream = diaspy.streams.Stream(connection)
            except Exception:
                logging.warning("There was an error while connecting to Diaspora pod - we will try again next time NavierStokes is run.")
                continue

            aspect = 'public'
            if message.public == 0:
                aspect = self.aspect
                pass

            message_text = BeautifulSoup(message.content, "html.parser").get_text()
            message_text = message_text.replace('\n','\n\n')
            #message_text =   html2text.html2text(message.content)



            if len(message.attachments) > 0:
                # This is due to this bug: https://github.com/marekjm/diaspy/issues/22
                # Try to work around it for now.

                # Move the attachment to the local directory
                destination = message.attachments[0].split("/")[-1]
                shutil.move(message.attachments[0], destination)
                post_trials = 0
                while post_trials < 5:
                    has_exception = False
                    try:
                        stream.post(text=message_text, photo=destination, aspect_ids=aspect)
                    except Exception:
                        has_exception = True
                        if post_trials >= 4:
                            message_text += "\n\n" + message.link
                            stream.post(text=message_text, aspect_ids=aspect)
                            pass
                    if has_exception == True:
                        post_trials += 1
                        time.sleep(1)
                    else:
                        break
                    pass
                        

                # Remove the local copy of the image
                os.remove(destination)
                
            else:
                try:
                    stream.post(text=message_text, aspect_ids=aspect)
                except:
                    self.msg(0, "Unable to post message:\n%s" % (message_text))
                pass
            pass

        self.msg(0, "Wrote %d messages." % (len(messages)))
        return successful_id_list
