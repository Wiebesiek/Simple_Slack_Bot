import mysecrets
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

TOKEN = mysecrets.slack_token
DEFAULT_CHANNEL = mysecrets.default_slack_channel


def notify(mail, channel=DEFAULT_CHANNEL):
    try:
        client = WebClient(token=TOKEN)
        response = client.chat_postMessage(channel=channel, text=mail['Subject'])
        assert response["message"]["text"] == mail['Subject']
    except SlackApiError as e:
        logging.debug("slackhandler.py:: " + f"Response 'ok' : {e.response['ok']}")
        logging.debug("slackhandler.py:: " + "ERROR: " + e.response["error"])
    except AssertionError as e:
        logging.debug("slackhandler.py:: ASSERTION ERROR")

    logging.debug("slackhandler.py:: " + "message supplied is " + mail['Subject'])
