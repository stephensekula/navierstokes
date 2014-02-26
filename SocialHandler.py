import abc
__metaclass__  = abc.ABCMeta


import sys
import logging

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


