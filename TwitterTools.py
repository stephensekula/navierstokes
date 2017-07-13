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
#import commands
import time

import URLShortener

# Python Twitter API access
import twitter

from MessageObj import Message


class TwitterHandler(SocialHandler):
    """ a class to read and post to a GNU Social feed """
    def __init__(self,username,credentials,tokens,sharelevel="Public"):
        SocialHandler.__init__(self)
        self.username = ""
        self.credentials = [s.strip() for s in credentials] #get rid of any stray spaces in the credentials/tokens
        self.tokens = [s.strip() for s in tokens]
        self.sharelevel = sharelevel
        self.configfile = ""
        pass



    def tweet_get_images(self,medialinks=[]):
        #
        # Search a tweet for an image link. If there are any, hunt them
        # down for the images, and get those images
        #
        photo_attachments=[]
        if medialinks == None:
            return photo_attachments

        for photo_link in medialinks:
            # download the HTML page that holds the image
            photo_link_url = photo_link.media_url_https
            filename_match = re.search('.*/(.*)', photo_link_url, re.DOTALL)
            if filename_match:
                local_filename = "/tmp/%s" % (filename_match.group(1))
                if not os.path.exists(local_filename):
                    process = subprocess.Popen(["curl -m 120 --connect-timeout 60 -o %s %s" % (local_filename,photo_link_url)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()[0]
                    pass
                if "/tmp/%s" % (filename_match.group(1)) not in photo_attachments:
                    photo_attachments.append(local_filename)
                    pass
                pass
            pass

        return photo_attachments


    def gather(self):

        self.messages = []

        self.msg(0, self.texthandler("Gathering messages."))

        configstring = ""
        if self.configfile != "":
            configstring = '-P %s' % (self.configfile)
            pass

        username = self.username
        api = twitter.Api(tweet_mode='extended', consumer_key = self.credentials[0], consumer_secret=self.credentials[1], access_token_key=self.tokens[0],access_token_secret=self.tokens[1])

        statuses = api.GetUserTimeline(screen_name=self.username)

        message = Message()

        for status in statuses:
            message = Message()
            message_time_text = datetime.datetime.strptime(status.created_at, "%a %b %d %H:%M:%S +0000 %Y")
            message.date = calendar.timegm(message_time_text.timetuple())
            message.source = "Twitter"
            message.repost = status.retweeted
            if message.repost and status.retweeted_status != None:
                message.SetContent(status.retweeted_status.full_text)
                message.id = status.retweeted_status.id
            else:
                message.SetContent(status.full_text)
                message.id = status.id
            message.author = status.user.screen_name
            message.reply = True if (status.in_reply_to_status_id != None) else False
            message.direct = True if (message.content[0] == "@") else False
            if message.reply or message.direct:
                message.public = False
            else:
                message.public = True
                pass

            # Don't bother sharing replies across networks...
            if message.reply:
                continue

            if message.repost:
                message.SetContent( self.texthandler("From <a href=\"https://twitter.com/%s\">Twitter</a>: " % (username)) + message.content )
                pass

            message.attachments = []
            if message.repost:
                message.attachments = self.tweet_get_images(status.retweeted_status.media)
            else:
                message.attachments = self.tweet_get_images(status.media)
                pass

            self.messages.append(message)
            pass

        self.messages = sorted(self.messages, key=lambda msg: msg.date, reverse=False)

        if self.debug:
            print("********************** Twitter Handler **********************\n")
            print("Here are the messages I gathered from the Twitter account:\n")
            for message in self.messages:
                print(message.Printable())
                pass

            pass


        return self.messages


    def write(self, messages):

        successful_id_list = []

        # initialize the connection to Twitter
        username = self.username
        api = twitter.Api(tweet_mode='extended', consumer_key = self.credentials[0], consumer_secret=self.credentials[1], access_token_key=self.tokens[0],access_token_secret=self.tokens[1])


        for message in messages:

            if message.content == "":
                continue

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
            message_text = copy.deepcopy(message.content)
            if len(message_text) > 140:
                if len(message.attachments) > 0:
                    message_text = message_text[:50] + "... " + message.link
                else:
                    message_text = message_text[:80] + "... " + message.link
                    pass

                pass

            if len(message_text) <= 140:
                tweet = message_text
                tweet = tweet.replace('\n',' ')
                tweet = tweet.replace("'","'\\\''")
                tweet = tweet.replace("@","")

                status = None
                try:
                    if len(message.attachments) > 0:
                        status = api.PostUpdate(tweet, media=message.attachments[0])
                    else:
                        status = api.PostUpdate(tweet)
                        pass
                except twitter.error.TwitterError:
                    self.msg(0, "Unable to post a message to twitter due to twitter.error.TwitterError")
                    self.msg(0, self.texthandler(message_text))
                    pass

                if status != None and status.created_at != None:
                    successful_id_list.append( message.id )

                pass

            else:
                # message is too long to post - print it to screen to help debug
                self.msg(0, "Unable to post a message to twitter, even after shortening - too long!")
                self.msg(0, self.texthandler(message_text))



            pass

        self.msg(0,"Wrote %d messages" % len(messages))
        return successful_id_list
