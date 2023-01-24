# NavierStokes

NavierStokes is a set of Python classes that allow you to bridge between social network accounts. These classes rely on a number of external tools to do the hard work of actually talking to networks. There is a master “executable” file that uses the supporting classes to bridge between your various accounts. See usage information below.

It employs “fuzzy text matching”, as well as a record of posts that have already been shared between networks, to try to prevent a post from being shared more than once to other networks (or back to the originating network). Fuzzy text matching is needed because different social networks encode or format the same information slightly differently. For instance, a post in HTML on Pump.io will not be formatted in HTML on Twitter, and Twitter will shorten links, thus altering the text of the original post. Fuzzy text matching uses statistical methods to attempt to compute the probability that the message has already been shared on a network. Above a match threshold, the post will not be shared.

NavierStokes considers only posts made within a time window (default is 1 hour) when it scans the streams from different social networks. It won't re-post something that is 6 hours or 6 days old ... unless you want it to (this can be controlled from the configuration file for each service).

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

I strongly recommend creating an encapsulated Python 3.X environment using pip or conda. Below I give guidance on doing this with conda.

```
conda create -n navierstokes python==3.11

conda activate navierstokes

conda install ConfigParser sets bs4 lockfile requests requests-oauthlib pycurl chardet

# Some things are just easier with Pip
pip install pypump diaspy-api twitter Mastodon.py html2text pyshorteners feedparser fuzzywuzzy python-Levenshtein lxml
```

# Installation

```
git clone git@github.com:stephensekula/navierstokes.git

conda activate navierstokes

cd navierstokes/
```

You should create a configuration file for NavierStokes: ~/.navierstokes/navierstokes.cfg. The syntax for the file is explained below.

You will need to register a new application on some platforms. The ```pump_register.py``` and ```mastodon_register.py``` scripts help with this and only require you to provide a webfinger (e.g., ```username@website```) to start the process.

Some credentials need to be entered into the configuration file (see below).

## Example navierstokes.cfg file

Be sure to make this .cfg file only readable by you:

```
chmod 600 ~/.navierstokes/navierstokes.cfg
```

Here is example syntax for the file:


```
[gnusocial]
type: gnusocial
site: gnusocial.server.url
username: myname
password: XXXXXXXXXXXXXXXX
sharelevel: Public
max_message_age: 3600

[pump.io]
type: pump.io
webfinger: user@pump.server
sharelevel: All
max_message_age: 86400

[mastodon]
type: mastodon
webfinger: user@mastodon.server
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
username: myname
client_credentials: abcd1234,wxyz6789
client_tokens: efgh2345,stuv4567


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

### The meaning of client_credentials for Twitter
For Twitter, this set of lists holds the following items. client_credentials holds the consumer key, followed by the consumer secret (comma-separated), that you get when you register NavierStokes in your twitter account as a new app (apps.twitter.com). The client_tokens list holds, in order, the access token and the access token secret (again, comma-separated) that you get from that same registration process.

### The meaning of other configuration keys
Note that “sharelevel” means at what level of publicity from other networks you want a notice shared to this one. I've set this, for now, the way I like it. If you set this to “Public”, ONLY notices that are public on other networks will go there. For instance, I only like to share things that are public on pump.io with Twitter. Things on Twitter are public by default, so they will ALWAYS be shared with other networks.

"max_message_age" controls how old a message can be and still be posted across your networks. The value is seconds from the time NavierStokes is run. The default is 3600s (1 hour).

“shortenurls” presently enabled will take ALL URLs listed in the message text and shorten them via ur1.ca. In the future, this will be a choice the user can make.
Running NavierStokes

"urlshortening" currently supports ur1.ca (and sites running its source) and shortenizer shortening. ur1.ca is the default shortening service/url.

Once you have written a .cfg file and setup account information in it (and, in the case of Pump.io and Twitter, you have authenticated PyPump and t against those respective networks as clients), you can try executing NavierStokes manually:

```
python ./NavierStokes.py
```

If you get errors, try running in Debug Mode and see what you can learn:

```
python ./NavierStokes.py -d
```

If you want to rate-limit posting, so that no more than N posts are bridged per execution, do this:

```
python ./NavierStokes.py -r 5
```

This ensures that no more than 5 posts are bridged to any network from any other network. This is useful for bot-scripts, especially if the script has not run for a while (due to server problems) and suddenly runs, gathering a large back-log of messages from social networks.

You can NavierStokes periodically (e.g every 5 minutes) using a CRON job:

```
*/5 * * * * bash -l -c 'source activate ~/anaconda/envs/navierstokes; python /path/to/navierstokes/NavierStokes.py -r 5 >> ${HOME}/.navierstokes/navierstokes.log 2>&1'
```

If you get any errors that are unrelated to passwords, logging in, or other authentication issues, then report them via the issue tracker on Github..
```
