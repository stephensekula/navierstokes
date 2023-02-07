"""
MastodonTools.py
Author: Stephen J. Sekula
Created: Jan. 24, 2023

* MastodonHandler:
Inherits from: SocialHandler
Purpose: to gather messages from a Mastodon instance, and write messages to
the same instance. This relies on the Mastodon.py interface to the Mastodon API.
"""

from SocialHandler import *
from MessageObj import Message

import subprocess
import os
import re
import calendar
import datetime
import subprocess
import codecs
from mastodon import Mastodon
import json
import html2text
import shutil
import time
from bs4 import BeautifulSoup
import json

class MastodonHandler(SocialHandler):
    def __init__(self, webfinger, token, sharelevel="Public"):
        SocialHandler.__init__(self)
        self.webfinger = webfinger
        self.token = token
        self.sharelevel = sharelevel

        pass



    def gather(self):

        self.messages = []

        try:
            m = Mastodon(access_token=self.token, api_base_url=f"https://{self.webfinger.split('@')[1]}")
        except Exception as e:
            self.msg(0,"Exception while establishing connection to Mastodon instance:")
            self.msg(0,e)
            return self.messages

        id=m.me()['id']

        statuses=m.account_statuses(id=id)

        for post in statuses:

            # Reject posts that are replies to other posts in Mastodon
            if post['in_reply_to_id'] != None:
                continue

            msg = Message()
            msg.source = "Mastodon"
            msg.id = post['id']
            msg.link = post['uri']
            msg.author = post['account']['display_name']
            msg.date   = calendar.timegm(post['created_at'].timetuple())
            msg.repost = post['reblog'] != None

            if msg.repost == False:
                msg.SetContent(msg.content + BeautifulSoup(post["content"], "html.parser").get_text())
            else:
                msg.SetContent(f'From {post["reblog"]["account"]["acct"]} on Mastodon: ' + BeautifulSoup(post["reblog"]["content"], "html.parser").get_text())
                
            # harvest media from the post
            for medium in post['media_attachments']:
                post_attachment = medium["url"]
                filename = post_attachment.split('/')[-1]
                if not os.path.exists(f'/tmp/{filename}'):
                    os.system(f'curl --connect-timeout 60 -m 120 -s -o /tmp/{filename} {post_attachment}')
                    pass
                msg.attachments.append( f'/tmp/{filename}' )
                pass

            # determine the message type
            msg.direct = False

            if post['visibility'] == 'public':
                msg.public = 1
            else:
                msg.public = 0

            self.messages.append(msg)

        self.messages = sorted(self.messages, key=lambda msg: msg.date, reverse=False)

        if self.debug:
            self.PrintBanner("Mastodon Handler", "*")
            self.msg(0, "Here are the messages I gathered from the Mastodon server:\n")
            for message in self.messages:
                print(message.Printable())
                pass

        return self.messages


    def write(self, messages=[]):

        successful_id_list = []

        # create a connection to the pod and write
        try:
            m = Mastodon(access_token=self.token, api_base_url=f"https://{self.webfinger.split('@')[1]}")
        except Exception as e:
            self.msg(0,"Exception while establishing connection to Mastodon instance:")
            self.msg(0,e)
            return self.messages

        id=m.me()['id']

        for message in messages:

            self.msg(0,"writing to Mastodon")

            do_write = True
            if message.public == False:
                self.msg(0,message.content)
                self.msg(0,"Unable to share message based on sharelevel settings.")
                do_write = False
                pass

            if not do_write:
                continue



            aspect = 'public'
            if message.public == 0:
                aspect = self.aspect
                pass

            media_ids=[]

            if len(message.attachments) > 0:
                for attachment in message.attachments:
                    media_ids.append(m.media_post(attachment))
            
            try:
                message_text = BeautifulSoup(message.content, "html.parser").get_text()
                m.status_post(message_text, media_ids=media_ids)
                successful_id_list.append( message.id )
            except:
                self.msg(0, "Unable to post message:\n%s" % (message.content))
            pass
            
            if len(message.attachments) > 0:
                for attachment in message.attachments:
                    os.remove(attachment)


        self.msg(0, "Wrote %d messages." % (len(successful_id_list)))
        return successful_id_list
