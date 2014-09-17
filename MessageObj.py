import datetime
import time
import codecs
import unicodedata

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
        self.public = 0
        self.link = ""
        self.source = ""
        pass

    def Printable(self):
        printable = ""
        printable += "======================== MESSAGE OBJECT ========================\n"
        printable += "FROM:    %s\n" % (self.author)
        
        printable += "DATE:    %s\n" % ((datetime.datetime.fromtimestamp(time.mktime(time.localtime(self.date)))).strftime('%Y %B %d %H:%M:%S'))
        printable += "ID:      %d\n" % (self.id)
        printable += "SOURCE:  %s\n" % (self.source)
        printable += "REPLY?:  %d\n" % (self.reply)
        printable += "PUBLIC?: %d\n" % (self.public)
        printable += "DIRECT?: %d\n" % (self.direct)
        printable += "REPOST?: %d\n" % (self.repost)
        try:
            printable += self.content
        except UnicodeDecodeError:
            printable += u"CONTENT: %s\n" % (unicodedata.normalize('NFKD',self.content).encode('ascii','ignore'))
            pass
        printable += "ATTACHMENTS: %s\n" % (str(self.attachments))

        if type(printable) == unicode:
            return unicodedata.normalize('NFKD', printable).encode('ascii','ignore')
        else:
            return printable

    def Print(self):
        print self.Printable()
        
    def SetContent(self, text):
        self.content = text
