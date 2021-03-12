import mysecrets
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

TOKEN = mysecrets.slack_token
DEFAULT_CHANNEL = mysecrets.default_slack_channel
USERS = ['<!here>',
         '<@' + mysecrets.user1_id + '>',
         '<@' + mysecrets.user2_id + '>']


class SlackHandler:

    def __init__(self):
        self.current_ts = float(0)
        # todo: change mysecrets playground id
        self.default_channel_id = mysecrets.playground_id
        self.token = TOKEN

    # can define timestamp to be used for new messages
    def get_new_messages(self, time_stamp=None):
        history = ""
        if time_stamp is None:
            time_stamp = self.current_ts

        try:
            client = WebClient(token=self.token)
            history = client.conversations_history(channel=self.default_channel_id, limit=10)
        except SlackApiError as e:
            logging.debug("slackhandler.py:: " +
                          "ERROR: fetching new slack messages" +
                          e.response["error"])

        # get only new messages
        new_messages = []
        try:
            if history.data:
                for m in history.data['messages']:
                    message_ts = float(m['ts'])
                    if message_ts > time_stamp:
                        new_messages.append(m)
                        logging.debug("slackhandler.py:: " +
                                      "Slack Message Found" +
                                      m['text'])
                        # update objects timestamp
                        if message_ts > self.current_ts:
                            self.current_ts = message_ts
        except:
            logging.debug("slackhandler.py:: " +
                          "ERROR: Problem reading conversation history")

        return new_messages


def users_pinged_in_messages(msg_dict):
    pinged_users = []
    for m in msg_dict:
        text = m['text']
        for u in USERS:
            if u in text:
                if u not in pinged_users:
                    pinged_users.append(u)

    return pinged_users


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
