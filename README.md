# Simple_Slack_Bot
A basic slack bot that will post when emails are received.

## Installation
1. Create virtual environment with preferred method.
2. Install requirements via pip install -r requirements.txt 
3. python slackbot.py install
4. Configure service to be run with credentials that the virtual environment is running in.

## Troubleshooting Installation
If you are receiving errors starting the service, try to run the program from the virtual environment:

 -- python slackbot.py debug

If this launches from here, but not the service, it is more than likely a permissions issue.

Here is a [stack exchange link](https://stackoverflow.com/questions/13466053/all-python-windows-service-can-not-starterror-1053) discussing some similar issues.


