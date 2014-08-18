# Code Originally Written By: Jon Robbins
# Modified by: Stephen Sekula

#this requires requests and only works with python2
# https://pypi.python.org/pypi/requests/0.13.0
import requests
import logging

FORMAT = "%(asctime)-15s %(message)s"
logging.basicConfig(format=FORMAT,level=logging.INFO)


class URLShortener(object):
    def __init__(self):
        # Eventually, this will allow the user to specify the shortening service.
        # For now, ur1.ca is hard-coded.
        # So init() does nothing.
        pass
        
    def getURLfromUR1caResponse(self, response):
        #response:
        #...
        #<p class="success">Your ur1 is: <a href="http://ur1.ca/hzm8a">http://ur1.ca/hzm8a</a></p>
        #...
        prefx       = '<p class="success">Your ur1 is: <a href="'
        linkClose   = '">'
        postfx      = '</a>'

        if not prefx in response:
            return "failure"    

        pos = 0        
        pos = response.find(prefx,pos)
        if pos < 0:
            return "failure"
            
        htmlText = response[pos:response.find(postfx,pos) + len(postfx)]
        #print "htmlText:" + htmlText
        
        link = htmlText[htmlText.find(prefx)+len(prefx):]
        link = link[:link.find(linkClose)]
        linkmsg = htmlText[htmlText.find(linkClose)+len(linkClose):htmlText.find(postfx)]
        #print "linkmsg: " + linkmsg
        
        return link

    def getUR1ca(self, longurl):

        # try to request the short URL from the shortener 5 times
        # before giving up

        tries = 0

        while tries < 5:
            payload = {'longurl':longurl}
            r = requests.post('http://ur1.ca', data=payload)
            if r.status_code == 200:
                break
            tries += 1
            sleep(5)
        
        if tries == 5:
            logging.error("Unable to connect to URL shortening site.")
            sys.exit(-1)
        
        
        shortURL = self.getURLfromUR1caResponse(r.text)
        
        if len(longurl) <= len(shortURL):
            return longurl
        else:
            return shortURL
        
