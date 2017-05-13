import datetime
import time
import codecs
import unicodedata

class Message:
    def __init__(self):
        self.title   = ""
        self.content = ""
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
        printable += \
"======================== MESSAGE OBJECT ========================\n \
FROM:    %(author)s\n \
DATE:    %(datetime)s\n \
ID:      %(id)d\n \
SOURCE:  %(source)s\n \
LINK:    %(link)s\n \
REPLY?:  %(reply)d\n \
PUBLIC?: %(public)d\n \
DIRECT?: %(direct)d\n \
REPOST?: %(repost)d\n" % {'author': self.author, 'datetime': ((datetime.datetime.fromtimestamp(time.mktime(time.localtime(self.date)))).strftime('%Y %B %d %H:%M:%S')), 'id': self.id, 'source': self.source, 'reply': self.reply, 'public': self.public, 'direct': self.direct, 'repost': self.repost, 'link': self.link}



        printable += str(self.content)
        printable += "\n"

        #except UnicodeDecodeError:
        #    printable += unicode("CONTENT: %s\n" % (unicodedata.normalize('NFKD',self.content).encode('ascii','ignore')))
        #    pass
        printable += "ATTACHMENTS: %s\n" % (str(self.attachments))

        return printable

    def Print(self):
        print(self.Printable())

    def SetContent(self, text=""):
        self.content = text
