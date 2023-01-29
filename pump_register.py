#!/usr/bin/env python
import sys
from pypump import PyPump, Client

# Pass the webfinger for your account to this script and follow its instructions
webfinger = sys.argv[1]

print(f"Setting up PyPump as an app registered for {webfinger}")

client = Client(
    webfinger=webfinger,
    type="native", # Can be "native" or "web"
    name="NavierStokes"
)


def simple_verifier(url):
    print('Go to: ' + url)
    return input('Verifier: ') # they will get a code back

pump = PyPump(client=client, verifier_callback=simple_verifier)
me   = pump.Person(webfinger)
print("Account information:")
print(webfinger)
print(me.summary)
