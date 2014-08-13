import abc
__metaclass__  = abc.ABCMeta


import sys
import os
import logging
import unicodedata
import commands
import re

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
    
    def HTMLConvert(self, msg ):
        msg_clean = msg.replace('<hr>','<p>')
        
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
        
        # First, determine if there is HTML already present
        newmsg = msg
        if msg.find('<a') != -1:
            newmsg = msg
        else:
            pattern = re.compile('(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[\(\)!*,]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)')

            newmsg = pattern.sub(r'<a href="\1">\1</a>', msg)
            
            pass

        return newmsg
        
