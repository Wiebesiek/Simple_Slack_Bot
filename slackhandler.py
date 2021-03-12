import mysecrets
import logging
import csv

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

TOKEN = mysecrets.slack_token
DEFAULT_CHANNEL = mysecrets.default_slack_channel


class SlackHandler:
    def __init__(self):
        self.phonebook = {}
        with open('phonebook.csv') as file:
            csv_file = csv.DictReader(file)
            for row in csv_file:
                self.phonebook[row['Username']] = row['Phone_Number']


def _get_from_address(str):
    return str[str.find("<")+1:str.find(">")]


def notify(mail, channel=DEFAULT_CHANNEL):
    if(_get_from_address(mail["From"]) == mysecrets.ticket_system_email_address):
        message_for_slack = mail['Subject'] + " <!here>"
    else:
        # todo: for testing purposes
        message_for_slack = mail['Subject']

    try:
        client = WebClient(token=TOKEN)
        response = client.chat_postMessage(channel=channel, text=message_for_slack)
        assert response["message"]["text"] == message_for_slack
    except SlackApiError as e:
        logging.debug("slackhandler.py:: " + f"Response 'ok' : {e.response['ok']}")
        logging.debug("slackhandler.py:: " + "ERROR: " + e.response["error"])
    except AssertionError as e:
        logging.debug("slackhandler.py:: ASSERTION ERROR")

    logging.debug("slackhandler.py:: " + "message supplied is " + message_for_slack)
