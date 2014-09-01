import abc
__metaclass__  = abc.ABCMeta


import sys
import os
import subprocess
import logging
import unicodedata
import commands
import re
import URLShortener


class SocialHandler(object):
    def __init__(self):
        # the list of messages gathered from this
        # social network's feed (e.g. your feed)
        self.messages = []

        # a map of users (strings) from another network
        # to users on this network (really, any old mapping
        # of string you like - good for putting hyperlinks to
        # users for discovery on other networks, or notification
        # purposes.
        self.usermap = {}

        # debug flag
        self.debug = False

        # shorten URLs in message content?
        self.do_url_shortening = False
        
		# URL shortening config to use
		self.urlShorteningConfig = {}

        # time limit for considering posts in this service (seconds)
        self.max_message_age = 3600

        # check that lynx is installed and accessible
        lynx_check = ""
        try:
            lynx_check = subprocess.check_output(["lynx", "--help"])
        except subprocess.CalledProcessError:
            self.msg(3, "Lynx is required, but I cannot run it. Make sure it is installed and located in the PATH.")
            pass
        except OSError:
            self.msg(3, "Lynx is required, but I cannot run it. Make sure it is installed and located in the PATH.")
            pass
        
        
        return

    @abc.abstractmethod
    def gather(self):
        """ This method harvests posts from a social network """

    @abc.abstractmethod
    def write(self,message=""):
        """ This method posts a message to a social network """

    def reshare_text(self, owner="someone"):
        """ This method returns common text that can be used to
        prepend to a reshared post"""
        text = "RT from %s" % (owner)
        return text

    def msg(self,level=0,text=""):
        level_text = "INFO"
        message = "%s: %s" % (self.__class__.__name__, text)

        if level == 0:
            logging.info(message)
        elif level == 1:
            logging.warning(message)
        elif level == 2:
            logging.error(message)
        elif level == 3:
            logging.critical(message)
            pass
        
        #print "%s: [%s] %s" % (self.__class__.__name__, level_text, text)
        
        
        if level > 2:
            sys.exit()
        
        return

    def map_users(self, text=""):
        new_text = text
        for key in self.usermap:
            new_text = new_text.replace(key, '<a href="%s">%s</a>'%(self.usermap[key][0],self.usermap[key][1]))
            pass
        return new_text


    def which(self,program):
        import os
        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        fpath, fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file
                    
        return None

    def changeLinksToURLs(self, msg):
        prefx       = '<a href='
        linkClose   = '">'
        postfx      = '</a>'
 
        if not prefx in msg:
            return msg    
        #<a href="http://www.thisisalink.com/foo/bar.html">this is some link text</a>
        #to
        #this is some link msg http://www.thisisalink.com/foo/bar.html

        pos = 0        
        while True:
            pos = msg.find(prefx,pos)
            if pos < 0:
                break
                
            htmlText = msg[pos:msg.find(postfx,pos) + len(postfx)]
             
            link = htmlText[htmlText.find(prefx)+len(prefx)+1:htmlText.find(linkClose)]
            linkmsg = htmlText[htmlText.find(linkClose)+len(linkClose):htmlText.find(postfx)]

            outText = linkmsg + ' ' + link

            if linkmsg == link:
                outText = link
             
            msg = msg.replace(htmlText, outText)
    
            pass

        return msg

    def HTMLConvert(self, msg ):
        msg_clean = self.changeLinksToURLs(msg)
        
        pid = os.getpid()

        htmlfile = open('/tmp/%d_msg.html' % (pid),'w')
        try:
            htmlfile.write( msg_clean )
        except UnicodeEncodeError:
            htmlfile.write( unicodedata.normalize('NFKD', msg_clean).encode('ascii','ignore') )
            pass

        htmlfile.close()
        
        txt = commands.getoutput('/usr/bin/lynx --dump -width 2048 -nolist /tmp/%d_msg.html' % (pid))

        os.system('rm -f /tmp/%d_msg.html' % (pid))

        return txt


    def TextToHtml(self, msg ):
        # Convert links to HTML in a text message
        # Relied on external tool, txt2html

        # write message to file for conversion
        pid = os.getpid()
        text_file = open("/tmp/txt2html_%d.txt" % (pid), "w")

        text_file.write(msg)

        text_file.close();

        # Convert using tool
        html_message = ""
        try:
            html_message = subprocess.check_output(["txt2html", "--infile", "/tmp/txt2html_%d.txt" % (pid)])
        except subprocess.CalledProcessError:
            print "There was a problem trying to call the txt2html program - make sure it is installed correctly."
            sys.exit(-1)
            pass
            
        # excerpt the content of the <body> tags
        
        body_begin = html_message.find('<body>') + 6
        body_end   = html_message.find('</body>')

        html_message = html_message[body_begin:body_end]

        return html_message


    def ShortenURLs(self, text):
        # convert all links in HTML to shortened links using a shortening service

        # Get all URLs from this text string

        found_urls = re.findall('(?:http[s]*://|www.)[^"\'<> ]+', text, re.MULTILINE)

        if len(found_urls) == 0:
            return text

        url_shortener = URLShortener.URLShortener(self.urlShorteningConfig['service'],self.urlShorteningConfig['url'], self.urlShorteningConfig['key'])

        new_text = text

        for url in found_urls:
            shortened_url = url_shortener.shorten(url)
            
            try:
                new_text = new_text.replace(url, shortened_url)
            except UnicodeDecodeError:
                url = url.encode('utf-8')
                shortened_url = shortened_url.encode('utf-8')
                new_text = new_text.replace(url, shortened_url)
                pass

            pass

        return new_text
        
            
            
            

        
