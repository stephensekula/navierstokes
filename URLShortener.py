# Code Originally Written By: Jon Robbins
# Modified by: Stephen Sekula

#this requires requests and only works with python2
# https://pypi.python.org/pypi/requests/0.13.0
import requests
import logging
import pycurl
try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

FORMAT = "%(asctime)-15s %(message)s"
logging.basicConfig(format=FORMAT,level=logging.INFO)

class CurlStorage:
    def __init__(self):
        self.contents = ''
        self.line = 0
        self.headers = {}

    def store(self,header_line):
        # HTTP standard specifies that headers are encoded in iso-8859-1.
        # On Python 2, decoding step can be skipped.
        # On Python 3, decoding step is required.
        header_line = header_line.decode('iso-8859-1')
        
        # Header lines include the first status line (HTTP/1.x ...).
        # We are going to ignore all lines that don't have a colon in them.
        # This will botch headers that are split on multiple lines...
        if ':' not in header_line:
            return
            
        # Break the header line into header name and value.
        name, value = header_line.split(':', 1)

        # Remove whitespace that may be present.
        # Header lines include the trailing newline, and there may be whitespace
        # around the colon.
        name = name.strip()
        value = value.strip()
        
        # Header names are case insensitive.
        # Lowercase name here.
        name = name.lower()

        # Now we can actually record the header name and value.
        self.headers[name] = value
    

    def __str__(self):
        return self.contents


def ExpandShortURL(short_url):
    buffer = BytesIO()

    retrieved_body = CurlStorage()
    retrieved_headers = CurlStorage()

    c = pycurl.Curl()
    c.setopt(c.URL, short_url)

    c.setopt(c.FOLLOWLOCATION, True)
    # Set our header function.
    c.setopt(c.WRITEFUNCTION, retrieved_body.store)
    c.setopt(c.HEADERFUNCTION, retrieved_headers.store)
    c.perform()

    c.close()

    original_url = short_url
    try:
        original_url = retrieved_headers.headers["location"]
    except KeyError:
        original_url = short_url


    return original_url


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
        
