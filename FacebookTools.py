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
import datetime
import calendar
import commands
import unicodedata

from MessageObj import Message


class FacebookHandler(SocialHandler):
    """ a class to read and post to a Facebook feed """
    def __init__(self,username="",sharelevel="Public",album="latest"):
        SocialHandler.__init__(self)
        self.sharelevel = sharelevel
        self.album = album
        # This is automatically searched for if blank. You can specific
        # it if you need to harvest/write as a page admin, etc.
        self.username = ""
        
        # check that fbcmd is installed
        self.active = True
        if self.which('fbcmd') == None:
            self.msg(0,unicode("fbcmd not installed; Facebook handler will be inactive"))
            self.active = False
            pass


        # Default commands - some users will post at themselves (default)
        # others as page owners or admins (allow for this)
        self.read_posts_command = "fbcmd fstream =me 120"
        self.read_pics_command = "fbcmd opics =me"
        self.write_post_command = "fbcmd status"
        self.write_pics_command = "fbcmd addpic"


        pass
 
    def fbcmd_error_status(self, fbcmd_output=""):
        if fbcmd_output.find("Application request limit reached") != -1:
            self.msg(0, self.texthandler("fbcmd unable to talk to Facebook due to limitations on application frequency by Facebook - Facebook operations stopped"))
            return 1
        return 0

    def gather(self):
        if not self.active:
            return []

        self.msg(0, self.texthandler("Gathering messages."))

        self.messages = []

        # enforce printing of date and formatting of date
        commands.getoutput('fbcmd SAVEPREF -stream_dateformat=\'Y D M d H:i Z\'')
        commands.getoutput('fbcmd SAVEPREF -stream_show_date=1')
        commands.getoutput('fbcmd SAVEPREF -pic_dateformat=\'Y D M d H:i Z\'')
        commands.getoutput('fbcmd SAVEPREF -pic_show_date=1')
        commands.getoutput('fbcmd SAVEPREF -stream_show_attachments=1')

        # first, determine my user name on Facebook (full name)
        # this is needed for filtering wall posts to only include those
        # posted by me (the current fbcmd user)

        fbcmd_whoami_text = self.texthandler(commands.getoutput('fbcmd whoami'))

        if self.fbcmd_error_status(fbcmd_whoami_text) != 0:
            return []

        matches = re.search('^[0-9]+  (.*)', fbcmd_whoami_text, re.DOTALL)

        username = self.username
        if username == "":
            if matches:
                username = self.texthandler(matches.group(1))
            else:
                self.msg(0,self.texthandler("Unable to determine your Facebook user name"))
                return self.messages;
            pass
            
        messages_text = self.texthandler(commands.getoutput('%s' % (self.read_posts_command)))

        if self.fbcmd_error_status(messages_text) != 0:
            return []

        #in_message = False
        #msg = Message()

        #inlink = False


        # First, find all blocks of text corresponding to unique posts (non photos first)
        messages_body_match = re.search('^.*?(\[1\].*)',messages_text,re.DOTALL)

        messages_text_noheader = self.texthandler("")

        if messages_body_match:
            messages_text_noheader = messages_body_match.group(1)
            pass

        facebook_message_blocks = re.split('\[[0-9]+\]\s+', messages_text_noheader, flags=re.DOTALL)

        for block in facebook_message_blocks:
            msg = Message()
            msg.source = "Facebook"

            # find date of message
            message_date_match = re.search('%s.*?([0-9]{4,4} .*?:[0-9][0-9]) ([-,\+][0-9]+)  ' % (username),block,re.DOTALL)
            if message_date_match:
                t = (datetime.datetime.strptime(message_date_match.group(1), '%Y %a %b %d %H:%M') - datetime.timedelta(seconds=int(message_date_match.group(2)))).timetuple()
                msg.date = calendar.timegm(t)
                pass
            else:
                self.msg(0,username)
                self.msg(0,block)
                self.msg(0,"Unable to obtain message date and time")
                continue
            
            # Get the message text and none of the comments, etc.

            message_text_match = re.search('.*[attach,link,photo,video] post  (.*)',block,re.DOTALL)
            if message_text_match != None:

                message_body = self.texthandler(message_text_match.group(1))
                
                message_text_match = re.search('.*?:(link|caption|name|desc).*',message_body, re.DOTALL)
                if message_text_match:
                    msg.repost = 1


                # remove links, etc.
                message_footer_match = re.search('(.*?):[link,desc,name,likes,caption].*',message_body,re.DOTALL)
                if message_footer_match:
                    message_body = message_footer_match.group(1)
                    pass


                # strip leading whitespace and ending whitespace.
                message_leading_whitespace = re.search('^\s+(.*)',message_body,re.DOTALL)
                if message_leading_whitespace:
                    message_body = message_leading_whitespace.group(1)
                    pass
                message_ending_whitespace = re.search('(.*?)\s+$',message_body,re.DOTALL)
                if message_ending_whitespace:
                    message_body = message_ending_whitespace.group(1)
                    pass

                message_body = re.sub('\s{3,100}',' ',message_body)

                msg.content = self.TextToHtml(message_body)
                msg.id = self.generate_id(msg.content)


                pass


            self.messages.append( msg )
            

        # handle images - they don't show up in the fstream
        messages_text = commands.getoutput('%s /tmp/fbcmd/ "-of=[pid].jpg"' % (self.read_pics_command))
        if self.fbcmd_error_status(messages_text) != 0:
            return []


        # strip the column header line
        message_header_search = re.search('^.*?CAPTION(.*)',messages_text,re.DOTALL)
        if message_header_search:
            messages_text = message_header_search.group(1)
            pass


        first_line_pattern = re.compile('((%s){0,1}\s+[0-9]+_[0-9]+\s+[0-9]{4} [A-Za-z]{3} [A-Za-z]{3} [0-9]{2} [0-9]{2}:[0-9]{2} [-,\+][0-9]+.*?)' % (username), flags=re.DOTALL)
        message_line_pattern = re.compile('^.*\s+([0-9]+_[0-9]+)\s+([0-9]{4} [A-Za-z]{3} [A-Za-z]{3} [0-9]{2} [0-9]{2}:[0-9]{2}) ([-,\+][0-9]+)(.*)')

        facebook_message_blocks = re.split('(^.*?[0-9]+_[0-9]+\s+[0-9]{4} [A-Za-z]{3} [A-Za-z]{3} [0-9]{2} [0-9]{2}:[0-9]{2} [-,\+][0-9]+)', messages_text, flags=re.MULTILINE)

        facebook_message_blocks = facebook_message_blocks[1:]

        for block_index in range(len(facebook_message_blocks)):
            if block_index % 2 != 0:
                continue
                
            pid_pattern = re.search('.*?\s+([0-9]+_[0-9]+)\s.*', facebook_message_blocks[block_index], re.DOTALL)
            if pid_pattern == None:
                continue

            photo_pid = pid_pattern.group(1)
            
            msg = Message()
            msg.source = "Facebook"
                    
            # find date of message

            message_date_match = message_line_pattern.search(facebook_message_blocks[block_index])
            datetext = ""
            dateoffset = ""
            if message_date_match:
                datetext = message_date_match.group(2)
                dateoffset = message_date_match.group(3)
                
                t = (datetime.datetime.strptime(datetext, '%Y %a %b %d %H:%M') - datetime.timedelta(seconds=int(dateoffset))).timetuple()
                msg.date = calendar.timegm(t)
                pass
            else:
                self.msg(0,"Unable to determine date and time of photo.")
                continue
                pass

            # attach image
            msg.attachments.append('/tmp/fbcmd/%s.jpg' % (photo_pid))

            # Get the content of the message
            message_body = facebook_message_blocks[block_index+1]

            # strip leading whitespace and ending whitespace.
            message_leading_whitespace = re.search('^\s+(.*)',message_body,re.DOTALL)
            if message_leading_whitespace:
                message_body = message_leading_whitespace.group(1)
                pass
            message_ending_whitespace = re.search('(.*?)\s+$',message_body,re.DOTALL)
            if message_ending_whitespace:
                message_body = message_ending_whitespace.group(1)
                pass

            message_body = re.sub('\s{3,100}',' ',message_body)


            msg.content = self.TextToHtml(self.texthandler(message_body))
            msg.id = self.generate_id(msg.content)


            self.messages.append( msg )
            



        self.messages = sorted(self.messages, key=lambda msg: msg.date, reverse=False)

        if self.debug:
            print "********************** Facebook Handler **********************\n"
            print "Here are the messages I gathered from the Facebook server:\n"
            for message in self.messages:
                print message.Printable()
                pass
            print "**************************************************************\n"

        return self.messages
    

    def write(self, messages):
        if not self.active:
            self.msg(0,"Facebook handler not active; no messages will be posted")
            return []

        write_count = 0

        successful_id_list = []

        for message in messages:

            self.msg(0,"writing to Facebook")
            self.msg(0,"Share level is: %s" % (self.sharelevel))

            
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
            
            if len(message.attachments) > 0:
                if self.debug:
                    self.msg(0,"   Posting a photo.")
                    pass

                for attachment in message.attachments:
                    if self.write_pics_command.find('ppost') != -1:
                        command = "%s \"%s\" %s %s" % (self.write_pics_command, message.content, message.link, message.link)
                    else:
                        command = "%s %s \"%s\" \"%s\"" % (self.write_pics_command, attachment, self.album, message.content)
                        pass

                    if self.debug:
                        self.msg(0, "   " + command)
                        pass
                    results = commands.getoutput(command)
                    if self.fbcmd_error_status(results) == -1:
                        successful_id_list.append( message.id )
                        pass
                        

                    pass
                pass
            else:
                command = "%s \"%s\"" % (self.write_post_command, message.content)
                if self.debug:
                    self.msg(0, "   " + command)
                    pass
                results = commands.getoutput(command)
                if self.fbcmd_error_status(results) == -1:
                    successful_id_list.append( message.id )
                    pass
                pass

            write_count += 1
            pass

        self.msg(0,"Wrote %d messages" % write_count)
        return successful_id_list

