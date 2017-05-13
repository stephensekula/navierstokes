# NavierStokes

NavierStokes is a set of Python classes that allow you to bridge between social network accounts. These classes rely on a number of external tools to do the hard work of actually talking to networks. There is a master “executable” file that uses the supporting classes to bridge between your various accounts. See usage information below.

It employs “fuzzy text matching”, as well as a record of posts that have already been shared between networks, to try to prevent a post from being shared more than once to other networks (or back to the originating network). Fuzzy text matching is needed because different social networks encode or format the same information slightly differently. For instance, a post in HTML on Pump.io will not be formatted in HTML on Twitter, and Twitter will shorten links, thus altering the text of the original post. Fuzzy text matching uses statistical methods to attempt to compute the probability that the message has already been shared on a network. Above a match threshold, the post will not be shared.

NavierStokes considers only posts made in the last hour when it scans the streams from different social networks. It won't re-post something that is 6 hours or 6 days old.

## Developers

Created by Stephen Sekula. Developers of this code are as follows:

* Jon Robbins (https://io.jrobb.org/jrobb)
* Stephen Sekula (https://hub.polari.us/steve)

## License

Copyright 2014, Stephen Jacob Sekula https://hub.polari.us/steve

Licensed under the Apache License, Version 2.0 (the “License”); you may not use this file except in compliance with the License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

# Requirements

    diapsy (Limited Diaspora access) (https://github.com/marekjm/diaspy)
    PyPump 0.5 (pump.io access)
        git clone https://github.com/xray7224/PyPump.git
        cd PyPump
        git fetch
        git checkout v0.5
    cURL (GNU Social access)
    LYNX (for converting HTML to plain text - some social networks don't understand HTML)
    FuzzyWuzzy Python fuzzy text-matching libraries
        https://github.com/seatgeek/fuzzywuzzy
        git clone https://github.com/seatgeek/fuzzywuzzy.git
        cd fuzzywuzzy
        python setup.py install
    t (Ruby Gem for interacting with Twitter)
        This is needed if you want to bridge to Twitter.
        http://rubygems.org/gems/t
        gem install t (requires Ruby 1.9 or greater)
    txt2html: needed for clean text → HTML conversion (e.g. from Twitter messages to Pump.io)

In general, here are the Python libraries needed to make this package operate:

```
abc
bs4
calendar
codecs
commands
copy
diaspy
feedparser
fuzzywuzzy
getopt
hashlib
inspect
lockfile
logging
math
os
pycurl
pypump
re
requests
subprocess
sys
time
unicodedata
xml.dom.minidom
```

# Installation

    Unpack the tarball. This automatically creates the navierstokes/ application directory
    You should create a configuration file for NavierStokes: ~/.navierstokes/navierstokes.cfg. The syntax for the file is explained below.
    If you intend to bridge between Pump.io and other networks, you must use PyPump to register a client (e.g. NavierStokesApp) on Pump.io. Follow their instructions for getting the client credentials and tokens. Enter those into the

    ~/.navierstokes/navierstokes.cfg

    file (see example below). PyPump docs: https://pypump.readthedocs.org/en/latest/
    Make sure Cliaspora is available in the PATH environment variable, or Diaspora interactions will fail.

## Example navierstokes.cfg file

Be sure to make this .cfg file only readable by you:

    chmod 600 ~/.navierstokes/navierstokes.cfg

```
[gnusocial]
type: gnusocial
site: gnusocial.server.url
username: myname
password: XXXXXXXXXXXXXXXX
sharelevel: Public

[pump.io]
type: pump.io
webfinger: user@pump.server
client_credentials: XXXXXXXXXXXXXXXXXXXXxx
client_tokens: XXXXXXXXXXXXXXXXXX
sharelevel: All

[diaspora]
type: diaspora
webfinger: user@diaspora.server
guid: XXXXXXXXXXXXXXXXXXX
password: XXXXXXXXXXXXXXXXXXX
aspect: public
sharelevel: All

[twitter]
type: twitter
sharelevel: Public
shortenurls: True

[my blog rss feed]
type: rss
feed_url: http://my.blog.example.com/rss/

[urlshortening]
service: shortenizer
serviceURL: http://u.jrobb.org
serviceKey: pseudosecretKey
#service: ur1
#serviceURL: http://ur1.ca
#serviceKey: False
```

Note that “sharelevel” means at what level of publicity from other networks you want a notice shared to this one. I've set this, for now, the way I like it. If you set this to “Public”, ONLY notices that are public on other networks will go there. For instance, I only like to share things that are public on pump.io with Twitter. Things on Twitter are public by default, so they will ALWAYS be shared with other networks.

“shortenurls” presently enabled will take ALL URLs listed in the message text and shorten them via ur1.ca. In the future, this will be a choice the user can make.
Running NavierStokes

"urlshortening" currently supports ur1.ca (and sites running its source) and shortenizer shortening. ur1.ca is the default shortening service/url.

Once you have written a .cfg file and setup account information in it (and, in the case of Pump.io and Twitter, you have authenticated PyPump and t against those respective networks as clients), you can try executing NavierStokes manually:

    python ./NavierStokes.py

If you get errors, try running in Debug Mode and see what you can learn:

    python ./NavierStokes.py -d

I run NavierStokes every 5 minutes using a CRON job:

```
*/5 * * * * bash -l -c 'python /path/to/navierstokes/NavierStokes.py >> ${HOME}/.navierstokes/navierstokes.log 2>&1'
```

If you get any errors that are unrelated to passwords, logging into, report them to navierstokes+NOSPAM@hub.polari.us.
A simple program to authenticate PyPump against your pump.io instance

For PyPump v0.5, this ought to work:

```
#!/usr/bin/env python

from pypump import PyPump, Client

client = Client(
    webfinger="ME@MY.PUMP",
    type="native", # Can be "native" or "web"
    name="NavierStokesApp"
)

def simple_verifier(url):
    print 'Go to: ' + url
    return raw_input('Verifier: ') # they will get a code back

pump = PyPump(client=client, verifier_callback=simple_verifier)
client_credentials = pump.get_registration() # will return [<key>, <secret>, <expirey>]
client_tokens = pump.get_token() # [<token>, <secret>]

print "client_credentials: %s,%s" % (client_credentials[0],client_credentials[1])
print "client_tokens: %s,%s" % (client_tokens[0],client_tokens[1])
```
