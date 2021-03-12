# don't use 3.9, currently using 3.7

import mysecrets
import re
import email
import logging
import slackhandler
from exchangelib import Credentials, Account, DELEGATE, Configuration, FaultTolerance, Message, Mailbox, CalendarItem
from exchangelib.items import MeetingCancellation, MeetingRequest
from imapclient import IMAPClient
from collections import deque


class emailhandler:
    def __init__(self, count=10, protocol='EWS'):
        self.last_ten_tickets = deque([], maxlen=count)
        self.protocol = protocol
        self.credentials = Credentials(mysecrets.username, mysecrets.password)
        self.config = Configuration(server=mysecrets.host,
                                    credentials=self.credentials,
                                    retry_policy=FaultTolerance())
        self.account = Account(primary_smtp_address=mysecrets.email_address,
                          config=self.config,
                          credentials=self.credentials,
                          autodiscover=False,
                          access_type=DELEGATE)

    # We have no use for calendar items
    def _delete_cal_items(self):
        cal = self.account.calendar.all()
        for c in cal:
            c.delete()

    # doesn't add ticket if it is already in the deque
    def add_ticket(self, ticket):
        if not self.last_ten_tickets.__contains__(ticket):
            self.last_ten_tickets.append(ticket)
            return ticket

    def process_emails(self, emails):
        if isinstance(emails, list):
            for mail in emails:
                ticket_num = self.add_ticket(_get_ticket_num(str(mail['Subject'])))
                if ticket_num:
                    logging.debug("sending message to slackhandler.notify")
                    slackhandler.notify(mail)

# returns array of new emails
    def get_emails(self):
        if self.protocol == 'IMAP':
            with IMAPClient(host=mysecrets.host) as client:
                # init IMAP connection
                client.login(mysecrets.username, mysecrets.password)
                client.select_folder('Inbox')

                # returns uids of emails
                messages = client.search(['UNSEEN'])

                # returns emails in a dictionary format
                email_dict = client.fetch(messages, ['RFC822'])
                client.add_flags(messages, '\\SEEN')

                # close out imap connection
                client.shutdown()
                emails = []

                # convert emails from dict format to email format
                for mail in email_dict.values():
                    emails.append(email.message_from_string(mail[b'RFC822'].decode("UTF-8")))

                return emails

        if self.protocol == 'EWS':
            self._delete_cal_items()
            # get unread emails
            unread = self.account.inbox.filter(is_read=False)
            logging.debug("emailhandler.py get_emails()::" + str(unread.count()))
            emails = []

            # convert from exchangelib.items.message.Message object to email object
            for mail in unread:
                emails.append(email.message_from_string(mail.mime_content.decode("UTF-8")))
                logging.debug("emailhandler.py get_emails unread email found ::" + str(mail.subject))

                # mark as read
                mail.is_read = True
                mail.save(update_fields=['is_read'])

            return emails

    # Sets the flag on all email to seen
    def read_all_emails(self):
        if self.protocol == 'IMAP':
            with IMAPClient(host=mysecrets.host) as client:
                client.login(mysecrets.username, mysecrets.password)
                client.select_folder('Inbox')
                messages = client.search(['UNSEEN'])
                client.add_flags(messages, '\\SEEN')
                client.shutdown()

        if self.protocol == 'EWS':
            self._delete_cal_items()
            # get unread emails
            unread = self.account.inbox.filter(is_read=False)
            for mail in unread:
                logging.debug('emailhandler.py:: Unread email found in read_all_emails: ' + str(mail.subject))
                mail.is_read = True
                # todo: save is returning a massive string - check documentation
                mail.save(update_fields=['is_read'])

    def send_email(self, email_address, subject, body):
        m = Message(account=self.account,
                    folder=self.account.sent,
                    subject=subject,
                    body=body,
                    to_recipients=[email_address])
        m.send_and_save()

    def process_pinged_users(self, pinged_users, message):
        for u in pinged_users:
            if u in mysecrets.phonebook.keys():
                self.send_email(mysecrets.phonebook[u],
                                subject='Slackbot Alert',
                                body=message)


# get ticket number from a valid high priority subject line
# If str in not in proper format, nothing is returned
def _get_ticket_num(subj):
    if subj.find("Priority 1") > -1:
        # emails follow the following format
        # Incident# 12345 is a Priority 1 ticket and has been assigned to your team
        pattern = re.compile(mysecrets.ticket_regex_string)
        if re.search(pattern, subj):
            num_str = re.search(r"\d+",subj)
            return int(num_str.group(0))

