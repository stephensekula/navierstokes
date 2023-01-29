# Code Originally Written By: Jon Robbins
# Modified by: Stephen Sekula

#this requires requests and only works with python2
# https://pypi.python.org/pypi/requests/0.13.0
import requests
import logging
import pycurl
import json
import time
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
    #c.setopt(c.USERAGENT, "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A")

    c.setopt(c.FOLLOWLOCATION, True)
    # Set our header function.
    c.setopt(c.WRITEFUNCTION, retrieved_body.store)
    c.setopt(c.HEADERFUNCTION, retrieved_headers.store)

    try:
        c.perform()
    except pycurl.error:
        return short_url
        pass

    c.close()

    original_url = short_url
    try:
        original_url = retrieved_headers.headers["location"]
    except KeyError:
        original_url = short_url

    if original_url[:4] != "http":
        print("URLShortener.ExpandShortURL(): attempt to retrieve original failed. Using shortened link.")
        original_url = short_url
        pass

    return original_url



class URLShortener(object):
    def __init__(self, urlShorteningConfig = {}):
        #supported url shortening services:
        serviceTypes = ['ur1','shortenizer']
        defaults = {'service':'ur1', 'url':'http://ur1.ca', 'key':False}

        #check if the service type is in the supported list (/in the dict at all):
        try:
            self.service = urlShorteningConfig['service']
        except KeyError:
            urlShorteningConfig = defaults

        if not self.service in serviceTypes:
            logging.warn("invalid serviceTYpe: ", self.service)
            logging.info("defaulting urlshortener to ur1.ca")
            urlShorteningConfig = defaults
            self.service = urlShorteningConfig['service']

        try:
            self.serviceURL = urlShorteningConfig['url']
            self.key = urlShorteningConfig['key']
        except KeyError:
            urlShorteningConfig = defaults
            self.service = urlShorteningConfig['service']
            self.serviceURL = urlShorteningConfig['url']
            self.key = urlShorteningConfig['key']

        #logging.info('init-ing the URLshortener')
        #logging.info('serviceType: ', self.service)
        #logging.info('serviceURL: ', self.serviceURL)
        #logging.info('key: ', self.key)

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
        #print("htmlText:" + htmlText)

        link = htmlText[htmlText.find(prefx)+len(prefx):]
        link = link[:link.find(linkClose)]
        linkmsg = htmlText[htmlText.find(linkClose)+len(linkClose):htmlText.find(postfx)]
        #print("linkmsg: " + linkmsg)

        return link

    def getUR1ca(self, longurl):

        # try to request the short URL from the shortener 5 times
        # before giving up

        tries = 0

        while tries < 5:
            payload = {'longurl':longurl}
            try:
                r = requests.post(self.serviceURL, data=payload)
                if r.status_code == 200:
                    break
            except requests.exceptions.ConnectionError:
                pass
            tries += 1
            time.sleep(5)

        if tries == 5:
            logging.error("Unable to connect to URL shortening site.")
            sys.exit(-1)


        shortURL = self.getURLfromUR1caResponse(r.text)

        if len(longurl) <= len(shortURL):
            return longurl
        else:
            return shortURL

    def getURLfromShortenizerResponse(self, response):
        #JSON response:
        #{
        #    'longURL': 'http://somelong.url/foo.bar'
        #    'shortURL': 'http://sho.rt/xyzf'
        #}
        response = json.loads(response)
        try:
            shortURL = response['shortURL']
        except:
            shortURL = 'errror'
            return response['error']
        print(shortURL)

        return shortURL

    def getShortenizer(self, longurl, vanityTerm=False):
        #  this sample POSTs to the shortenizer api and then gets the
        #  returned shortened short url from the JSON repsonse
        print('shortenizing')
        if not self.serviceURL:
            #error
            print('error, no serviceURL')
        if self.serviceURL[-1] != '/':
            self.serviceURL += '/'
        if not '/api/' in self.serviceURL:
            self.serviceURL += 'api/shorten/'

        payload = {'longurl':longurl, 'key':self.key, 'term':vanityTerm}
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        try:
            r = requests.post(self.serviceURL, data=json.dumps(payload), headers=headers, verify=False)
            r = r.text
            shortURL = self.getURLfromShortenizerResponse(r)
        except requests.exceptions.ConnectionError:
            r = 'error: Unable to connect to URL shortening site'
            logging.error(r)
            shortURL = r

        #print("response: \n", r, "---/response -- \n")

        return shortURL

    def shorten(self, longurl, vanityTerm=False):
        logging.debug('url shortening service: ', self.service)
        if self.service == 'shortenizer':
            shortURL = self.getShortenizer(longurl, vanityTerm)
        else:
            shortURL = self.getUR1ca(longurl)

        print("original URL length: " + str(len(longurl)))
        print("short URL length: " + str(len(shortURL)))
        if len(longurl) <= len(shortURL) or (shortURL[:6] == 'error:') or (shortURL[:8] == 'failure'):
            return longurl
        else:
            return shortURL

if __name__ == '__main__':
    #syntax for test is ie:
    # python shortenURL.py -u http://pump.io/tryit.html
    #python CLIshortenURL_test.py -u https://somelongurl.com/somelong/path/foo.bar -t shortenizer -s http://u.jrobb.org -k mykey
    import sys
    import getopt
    # Parse command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "s:u:t:v:k:", ["type=", "service=", "url=","vanity=","key="])
        print("opts: " + str(opts))
        print("args: " + str(args))
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err)) # will print something like "option -a not recognized"
        os.remove(path_to_pidfile)
        sys.exit(2)
        pass

    serviceURL = 'http://ur1.ca'
    vanityTerm = ''
    key = ''
    serviceType = 'ur1'
    for o, a in opts:
        if o in ("-u", "--url"):
            longurl = a
        elif o in ("-t", "--type"):
            serviceType = a
        elif o in ("-s", "--service"):
            serviceURL = a
        elif o in ("-v", "--vanity"):
            vanityTerm = a
        elif o in ("-k", "--key"):
            key = a
        else:
            assert False, "unhandled option"
            pass
        pass

    print("serviceTYpe: ", serviceType)
    print("longurl: ", longurl)
    print("serviceURL: ", serviceURL)
    print("term: ", vanityTerm)
    print("key: ", key)

    config = {'service':serviceType, 'url':serviceURL, 'key':key}

    myurl = URLShortener(config)
    if not longurl:
        print("error, no url, something's not right")
    else:
        #output the shortened URL
        print(myurl.shorten(longurl, vanityTerm))
