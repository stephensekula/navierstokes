"""
GNUSocialTools.py
Author: Stephen J. Sekula
Created: Dec. 23, 2013

* GNUSocialHandler:
Inherits from: SocialHandler
Purpose: to gather messages from a Statusnet/GNU Social instance, and write messages to
the same instance. It uses cURL and the API to do all of this.
It also uses Lynx to convert HTML to plain text for posting to GNU Social.
"""

from SocialHandler import *
import xml.dom.minidom
import sys

import subprocess
import os
import re
import time
import datetime
import calendar
import codecs
import subprocess


from MessageObj import Message


class GNUSocialHandler(SocialHandler):
    """ a class to read and post to a GNU Social feed """
    def __init__(self,username="",password="",site="",sharelevel="Public"):
        SocialHandler.__init__(self)
        self.username = username
        self.password = password
        self.site     = site
        self.sharelevel = sharelevel

        # Check for problems with the configuration
        if self.site.find('http') == -1:
            self.msg(2,'The GNU Social site name must include the preceding http or https in the URL.')
            sys.exit(-1)
            pass

        pass

    # functions for handling XML
    def get_a_stream(self,name="out.xml"):
        return xml.dom.minidom.parse(name)

    def find_status_elements(self,doc):
        list_of_status_elements = []
        #print(doc.toprettyxml())
        list_of_status_elements = doc.getElementsByTagName("status")
        #print(list_of_status_elements)
        return list_of_status_elements

    def find_element_of_status(self,status,element_name):
        element_content = ""
        for e in status.childNodes:
            if e.ELEMENT_NODE and e.localName == element_name:
                for t in e.childNodes:
                    # element_content = t.data.encode('utf-8').strip()
                    element_content = t.data.strip()
                    break
                pass
            pass

        return element_content

    def status_is_retweeted(self,status):
        for e in status.childNodes:
            if e.ELEMENT_NODE and e.localName == "retweeted_status":
                return True
            pass
        return False

    def status_author_name(self,status):
        name = ""
        for e in status.childNodes:
            if e.ELEMENT_NODE and e.localName == "user":
                for u in e.childNodes:
                    if u.ELEMENT_NODE and u.localName == "screen_name":
                        for t in u.childNodes:
                            # name = t.data.encode('utf-8').strip()
                            name = t.data.strip()
                            break
                        pass
                    pass
                pass
            pass
        return name


    def status_attachment(self,status):
        attachments = []
        for e in status.childNodes:
            if e.ELEMENT_NODE and e.localName == "attachments":
                for a in e.childNodes:
                    if a.ELEMENT_NODE and a.localName == "enclosure":
                        for (name,value) in a.attributes.items():
                            if name == 'url':
                                attachments.append(value)
                                pass
                            pass
                        pass
                    pass
                pass
            pass
        return attachments



    def gather(self):

        self.messages = []

        self.msg(0, "Gathering messages.")

        # Get the XML file from the web
        # try:
        xml_file_contents = subprocess.check_output('curl -m 120 --connect-timeout 60 -s -u \'%s:%s\' %s/api/statuses/user_timeline/%s.xml?count=200' % (self.username,self.password,self.site,self.username), shell=True).decode('utf-8')
        # except xml.parsers.expat.ExpatError:
        #     return self.messages

        pid = os.getpid()

        xml_file = codecs.open('/tmp/%d_dents.xml' % (pid),'w',encoding='utf-8')
        xml_file.write(self.texthandler(xml_file_contents))
        xml_file.close()

        try:
            document = self.get_a_stream("/tmp/%d_dents.xml" % (pid))
            dents_xml = self.find_status_elements(document)
        except xml.parsers.expat.ExpatError:
            return self.messages

        highest_id = 0
        for dent_xml in dents_xml:

            dent_source = self.find_element_of_status(dent_xml,"source")
            #if dent_source == "activity":
            #    continue

            dent_text = self.find_element_of_status(dent_xml,"text")
            dent_author = self.status_author_name(dent_xml)
            if dent_author != self.username:
                continue

            message = Message()
            message.source = "GNU Social"
            message.SetContent(dent_text)
            message.content = self.TextToHtml(message.content)
            if message.content.find("deleted notice") != -1:
                continue
            message.author = dent_author
            message.reply = True if self.find_element_of_status(dent_xml,"in_reply_to_status_id") != "" else False
            message.public = True

            message.id = int(self.find_element_of_status(dent_xml,'id'))

            message.link = f'{self.site}/conversation/{message.id}#notice-{message.id}'

            # if the dent has a @ at the beginning, it was meant to be a direct
            # message to someone on GNU social and should not be broadcast
            if dent_text[0] == "@":
                message.direct = 1

            dent_attachments = self.status_attachment(dent_xml)
            for dent_attachment in dent_attachments:
                if dent_attachment.find(self.site) != -1:
                    filename = dent_attachment.split('/')[-1]
                    if not os.path.exists('/tmp/%s' % (filename)):
                        os.system('curl --connect-timeout 60 -m 120 -s -o /tmp/%s %s' % ( filename, dent_attachment ))
                        pass

                    message.attachments.append( '/tmp/%s' % (filename) )
                    pass
                pass

            # Remove offset from timestamp and handle it separately - strptime cannot reliably handle %z in Python
            gs_msg_timestamp = self.find_element_of_status(dent_xml,"created_at")
            gs_msg_notz = gs_msg_timestamp[0:19]+" "+gs_msg_timestamp[26:]
            gs_msg_tzonly = gs_msg_timestamp[20:24]
            t = datetime.datetime.strptime(gs_msg_notz, "%a %b %d %H:%M:%S %Y") - datetime.timedelta(seconds=int(gs_msg_tzonly))
            message.date = calendar.timegm(t.timetuple())
            message.repost = self.status_is_retweeted(dent_xml)
            if message.repost:
                message.SetContent( "<a href=\"%s\">From GNU Social</a> : " % (self.find_element_of_status(dent_xml,"uri") + message.content ))
                pass


            self.append_message(message)
            pass

        self.messages = sorted(self.messages, key=lambda msg: msg.date, reverse=False)

        if self.debug:
            print("********************** GNU Social Handler **********************\n")
            print("Here are the messages I gathered from the GNU Social server:\n")
            for message in self.messages:
                print(message.Printable())
                pass

        # cleanup
        os.system('rm -f /tmp/%d_dents.xml' % (pid))

        return self.messages


    def write(self, messages):

        successful_id_list = []

        for message in messages:

            self.msg(0,"writing to GNU Social")
            self.msg(0,"Share level is: %s" % (self.sharelevel))

            data = ""

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

            pid = os.getpid()

            fout = codecs.open('/tmp/%d_statusnet_text.txt' % (pid),'w',encoding='utf-8')
            message.content = self.texthandler(message.content)
            try:
                fout.write('source=NavierStokesApp&status='+message.content)
            except UnicodeEncodeError:
                fout.write('source=NavierStokesApp&status='+message.content)
            fout.close()

            data += " -d @/tmp/%d_statusnet_text.txt" % (pid)
            if len(message.attachments)>0:
                if self.debug:
                    self.msg(level=0,text="Message has attachments.")
                    self.msg(level=0,text=str(message.attachments))
                    pass



                fout = codecs.open('/tmp/%d_statusnet_text.txt' % (pid),'w',encoding='utf-8')
                try:
                    fout.write(message.content)
                except UnicodeEncodeError:
                    fout.write(message.content)
                fout.close()

                data =  " -F source=NavierStokesApp"
                data += " -F \"status=</tmp/%d_statusnet_text.txt\"" % (pid)
                for attachment in message.attachments:
                    # convert image to png if it's not png
                    prefix = '.'.join(attachment.split('.')[:-1])
                    os.system("convert -scale 1024x768 %s %s_1024x768.png" % (attachment, prefix))

                    png_file = prefix + "_1024x768.png"
                    #if -1 == attachment.find('.png'):
                    #    png_file =  '.'.join(attachment.split('.')[:-1]) + '.png'
                    #    os.system('convert %s %s' %(attachment, png_file))
                    #    pass

                    data += " -F media=@" + png_file
                    pass


                pass

            command = 'curl --connect-timeout 60 -m 120 -s -u \'%s:%s\' %s/api/statuses/update.xml %s' % (self.username,self.password,self.site,data)
            if self.debug:
                self.msg(level=0,text=command)
                pass

            results = self.texthandler(subprocess.check_output(command, shell=True))
            if results.find("error") != -1:
                if results.find("Maximum notice size") != -1:
                    self.msg(level=2,text="Message too long to post to GNU Social - skipping...")
                elif results.find("A file this large would exceed your user quota") != -1:
                    self.msg(level=2,text="Message too large in bytes to post to GNU Social - skipping...")
                else:
                    self.msg(level=3,text=results)
                    self.msg(level=3,text="Unable to post this message")
                    pass
                pass
            else:
                successful_id_list.append( message.id )
            pass

        self.msg(0,"Wrote %d messages" % len(successful_id_list))
        return successful_id_list
