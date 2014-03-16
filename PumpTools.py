"""
PumpTools.py
Author: Stephen J. Sekula
Created: Dec. 23, 2013

* PumpHandler:
Inherits from: SocialHandler
Purpose: to gather messages from a pump.io instance, and write messages to
the same instance. It uses PyPump 0.4 to do all of this
(https://github.com/xray7224/PyPump)
"""

from SocialHandler import *
from pypump import PyPump, Client
from pypump.models.image import Image
from pypump.models.collection import Collection
from pypump.models.collection import Public
from pypump.models.person import Person
from pypump.exception import PyPumpException

from requests.exceptions import ConnectionError

from MessageObj import Message

import sys
import os
import inspect
import unicodedata
import time
import calendar
import codecs

import requests
from requests_oauthlib import OAuth1

class PumpHandler(SocialHandler):
    
    def __init__(self,webfinger,credentials,tokens):
        self.webfinger = webfinger
        self.credentials = credentials
        self.tokens = tokens

        self.pump = None
        self.me = None

        try:
            self.pump = self.CreatePumpClient(self.webfinger, self.credentials, self.tokens)
            self.me   = self.pump.Person(self.webfinger)
        except PyPumpException:
            print "Unable to initiate a connection to the pump server. Pump.io will be skipped."
            self.pump = None
            self.me = None
            pass
        except ConnectionError:
            print "The connection to the pump server has timed out. Pump.io will be skipped."
            self.pump = None
            self.me = None
            pass
            

        self.messages = []

        self.debug = False
        
        pass

    def simple_verifier(url):
        print 'Go to: ' + url
        return raw_input('Verifier: ') # they will get a code back

    def CreatePumpClient(self, webfinger, client_credentials,client_tokens):
        client = Client(
            webfinger=self.webfinger,
            type="native",
            name="NavierStokes",
            key=client_credentials[0],
            secret=client_credentials[1],
            )
        
        pump = PyPump(
            client=client,
            token=client_tokens[0], # the token
            secret=client_tokens[1], # the token secret
            verifier_callback=self.simple_verifier
            )
        
        return pump


    def gather(self):
        """ Gather messages from the pump """

        self.messages = []

        if not self.pump:
            return []

        for activity in self.me.outbox.major[:20]:
            pump_obj    = activity.obj
            pump_obj_id = activity.id

            message = Message()

            message.source = "Pump.io"

            # get the text into decent shape
            text = pump_obj.content
            #message.content = unicodedata.normalize('NFKD', unicode(text)).encode('ascii','ignore')
            #message.content = unicode(text).encode("utf-8")
            message.SetContent(text)
            
            try:
                if pump_obj.deleted:
                    continue
            except AttributeError:
                print "The arrtribute \"deleted\" does not exist . . . continuing anyway . . . "
                pass

            # Determine if this message was directed to someone on Pump.io and thus
            # isn't intended for sharing outside the network.
            to_list = getattr(activity, "to", [])
            if len(to_list) > 0:
                # was "Public" among the "To:" recipients? Then we can go on; otherwise,
                # skip this message
                is_direct = False
                is_public = False
                for person in to_list:
                    if isinstance(person, Person):
                        is_direct = True
                    elif isinstance(person, Collection):
                        if person.id.find("public") != -1:
                            is_direct = False
                            is_public = True
                            break
                        pass
                    pass
                
                if is_direct:
                    message.direct = 1
                if is_public:
                    message.public = 1
                    pass

                pass

            if isinstance( pump_obj, Image):
                img_url = pump_obj.original.url

                # construct a request to grab the image
                endpoint = "{0}".format('/'.join(img_url.split('/')[3:]))
                # remove "_thumb" from the image name to get the original image
                endpoint = endpoint.replace('_thumb','')
                local_img_name = endpoint.split('/')[-1]
                client = self.pump.setup_oauth_client(endpoint)
                params = {} 
                headers = {"Content-Type": "application/json"}
                request = {
                    "params": params,
                    "auth": client,
                    "headers": headers,
                    }
                
                image_raw = self.pump._requester(requests.get, endpoint, raw=False, **request)
                
                fout = open("/tmp/{0}".format(local_img_name), "w")
                fout.write(image_raw.content)
                fout.close()
                
                #message.content = unicodedata.normalize('NFKD', pump_obj.display_name).encode('ascii','ignore')
                #print ".display_name: %s" % (pump_obj.display_name)
                #print ".summary: %s" % (pump_obj.summary)
                #print ".content: %s" % (pump_obj.content)

                message.SetContent( pump_obj.content )
                if message.content == '':
                    message.content = 'An image...'
                    pass
                message.attachments.append("/tmp/{0}".format(local_img_name) )

            # 2013-12-18 17:56:37+00:00
            #print message.content
            #print pump_obj.published
            t = time.strptime(str(pump_obj.updated), "%Y-%m-%d %H:%M:%S+00:00")
            #message.date = time.mktime(t)
            message.date = calendar.timegm(t)

            message.author = pump_obj.author.display_name
            message.author_url = pump_obj.author.url
            

            #if str(message.author) != str(self.me):
            if message.author != self.me.display_name:
                message.repost = True
                message.SetContent( "RT from %s: " % (message.author) + message.content )
                pass

            self.messages.append(message)

            pass

        self.messages = sorted(self.messages, key=lambda msg: msg.date, reverse=False)

        if self.debug:
            print "********************** Pump.io Handler **********************\n"
            print "Here are the messages I gathered from the pump.io server:\n"
            for message in self.messages:
                message.Print()
                pass
            
        return self.messages


    def write(self, messages = []):

        if not self.pump:
            return

        for message in messages:
            if len(message.attachments)==0:
                new_note = self.pump.Note(message.content)
                new_note.send()
            else:
                new_note = self.pump.Image(display_name="",content=message.content)
                for attachment in message.attachments:
                    new_note.from_file(attachment)
                    pass
                pass
            pass

        self.msg(0, "Wrote %d messages." % (len(messages)))
        pass
