#!/bin/bash

###
### Install package dependencies for NavierStokes.
### 
###   * This could be run as part of a cron job that keeps the code up to date by git pulling, etc.
###

dependencies=" \
wheel
ConfigParser \
sets \
bs4 \
lockfile \
requests \
requests-oauthlib \
pycurl \
chardet \
lxml \
rfc2html \
thefuzz \
python-Levenshtein \
html2text \
pyshorteners \
feedparser
pypump \
diaspy-api \
twitter \
Mastodon.py \
"

pip install ${dependencies}


