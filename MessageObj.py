import time
import codecs

class Message:
    def __init__(self):
        self.content = unicode()
        self.id = 0
        self.file = ""
        self.date = 0
        self.author = ""
        self.author_url = ""
        self.reply = 0
        self.direct = 0
        self.repost = 0
        self.attachments = []
        pass

    def Print(self):
        print "======================== MESSAGE OBJECT ========================"
        print "FROM:    %s" % (self.author)
        print "DATE:    %s" % (time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.date)))
        print "ID:      %d" % (self.id)
        print "REPLY?:  %d" % (self.reply)
        print "DIRECT?: %d" % (self.direct)
        print "REPOST?: %d" % (self.repost)
        print "CONTENT: %s" % (self.content)
        print "ATTACHMENTS: %s" % (str(self.attachments))
        
    def SetContent(self, text):
        self.content = text
        # if all(ord(c) < 128 for c in text):
        #    self.content = text
        # else:
        #    print text
        #    self.content = unicode(text).encode("ascii")
        #    pass
        # pass
