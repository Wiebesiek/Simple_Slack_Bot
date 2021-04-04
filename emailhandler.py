# don't use 3.9, currently using 3.7

import mysecrets
import re
import email
import logging
import slackhandler
import my_parser
from exchangelib import Credentials, Account, DELEGATE, Configuration, FaultTolerance, Message
from imapclient import IMAPClient
from collections import deque


class emailhandler:
    def __init__(self, count=10, protocol='EWS'):
        self.last_ten_tickets = deque([], maxlen=count)
        self.protocol = protocol
        self.credentials = Credentials(mysecrets.username, mysecrets.password)
        self.on_call = _get_on_call_number_from_file(mysecrets.oncalltxt_location)
        self.permanent_numbers = mysecrets.permanent_numbers
        if not self.on_call:
            self.on_call = mysecrets.on_call
        self.config = Configuration(server=mysecrets.host,
                                    credentials=self.credentials,
                                    retry_policy=FaultTolerance())
        self.account = Account(primary_smtp_address=mysecrets.email_address,
                               config=self.config,
                               credentials=self.credentials,
                               autodiscover=False,
                               access_type=DELEGATE)
        self.phonebook = {}
        # with open('phonebook.csv') as file:
        #     csv_file = csv.DictReader(file)
        #     for row in csv_file:
        #         self.phonebook[row['Username']] = row['Phone_Number']

    # doesn't add ticket if it is already in the deque
    def add_ticket_num(self, ticket):
        if not self.last_ten_tickets.__contains__(ticket):
            self.last_ten_tickets.append(ticket)
            return ticket

    # Needs to be of email type and not exchangelib message
    def process_emails(self, emails):
        if isinstance(emails, list):
            for mail in emails:
                # Update on call logic
                on_call_phone_num = _on_call_update_email(mail)
                if on_call_phone_num:
                    self.on_call = on_call_phone_num
                    _update_on_call_file(on_call_phone_num)
                    logging.debug("emailhandler.py :: On call number has beeen updated to " + on_call_phone_num)
                    slackhandler.notifyOnCallUpdate(on_call_phone_num)

                # Who is on call request
                elif _on_call_request_email(mail):
                    logging.debug("emailhandler.py :: on call request notification" +
                                  " being sent to slackhandler")
                    slackhandler.notify_inform_who_is_on_call(self.on_call)

                # Priority 1 or 2 logic
                else:
                    num_pri_tuple = _get_ticket_num(str(mail['Subject']))
                    if num_pri_tuple:
                        ticket_num = self.add_ticket_num(num_pri_tuple[0])
                        if ticket_num:
                            # This block is reached if it's a new ticket to the bot
                            if num_pri_tuple[1] == 1:
                                logging.debug("emailhandler.py :: sending message to slackhandler.notify priority 1")
                                slackhandler.notifyP1(mail)
                                self.notify_on_call(mail, self.on_call)
                                for num in self.permanent_numbers:
                                    if num != self.on_call:
                                        self.notify_on_call(mail, num)
                            elif num_pri_tuple[1] == 2:
                                logging.debug("emailhandler.py :: sending message to slackhandler.notify priority 2")
                                slackhandler.notifyP2(mail)
                            else:
                                logging.ERROR("Invalid block reached in process_emails")

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
            # get unread emails
            unread = self.account.inbox.filter(is_read=False)
            logging.debug("emailhandler.py get_emails()::" + str(unread.count()))
            emails = []

            # convert from exchangelib.items.message.Message object to email object
            for mail in unread:
                try:
                    emails.append(_convert_from_exchange_email(mail))
                    logging.debug("emailhandler.py get_emails unread email found :: " + str(mail.subject))

                    # mark as read
                    mail.is_read = True
                    mail.save(update_fields=['is_read'])
                except:
                    logging.error("emailhandler.py:: ERROR in reading email. Not email?")

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
            # get unread emails
            unread = self.account.inbox.filter(is_read=False)
            for mail in unread:
                logging.debug('emailhandler.py:: Unread email found in read_all_emails: ' + str(mail.subject))
                mail.is_read = True
                # todo: save is returning a massive string - check documentation
                mail.save(update_fields=['is_read'])

    # mail needs to be of email type and not exchangelib message
    def notify_on_call(self, mail, phone_number):
        on_call_email_to_sms = phone_number + "@vtext.com"
        logging.debug("emailhandler.py :: Entering Notify_on_Call" +
                      "\n - Subject = " +
                      str(mail["Subject"]) +
                      "\n to_recipients = " +
                      on_call_email_to_sms)
        if phone_number:
            body_string = (mail["Subject"] +
                           "\n" +
                           "Center ID: " +
                           my_parser.get_cid(mail) +
                           "\n"
                           "Summary: " +
                           my_parser.get_summary(mail))

            message_to_send = Message(
                account=self.account,
                subject='',
                body=body_string,
                to_recipients=[on_call_email_to_sms]
            )
            try:
                message_to_send.send()
                logging.debug("emailhandler.py :: email sent to " + str(on_call_email_to_sms))
            except:
                logging.error("emailhandler.py :: FAILED TO SEND ON CALL TEXT")
        else:
            logging.debug("emailhandler.py :: Unable to send on call text, on_call is empty")


# get ticket number from a valid high priority subject line
# If str in not in proper format, nothing is returned
# Return tuple of (ticket_number, priority)
def _get_ticket_num(subj):
    # emails follow the following format
    # Incident# 12345 is a Priority 1 ticket and has been assigned to your team
    pattern = re.compile(mysecrets.ticket_regex_string)
    if re.search(pattern, subj):
        nums = re.findall(r"\d+", subj)
        return int(nums[0]), int(nums[1])


def _convert_from_exchange_email(mail):
    return email.message_from_string(mail.mime_content.decode("UTF-8"))


def _on_call_update_email(mail):
    if isinstance(mail, email.message.Message):
        if str(mail['Subject']).upper() == "UPDATE ON-CALL":
            # first payload seems to be body - This could change depending where and how it's sent
            # Should be consistent throughout enterprise
            logging.debug("emailhandler.py :: On-Call Update Found")
            phone_num_groups = ''
            for p in mail.get_payload():
                phone_num_groups = re.match(r"^\d{10}", p.get_payload())
                if phone_num_groups:
                    return phone_num_groups.group(0)


def _update_on_call_file(phone_number):
    try:
        with open(mysecrets.oncalltxt_location, 'w') as file_obj:
            file_obj.write(phone_number)
    except IOError as e:
        logging.error("emailhandler.py :: IO error recieved while trying to update oncall.txt")
    except:
        logging.error("emailhandler.py :: Unexpected occured trying to update oncall.txt")


def _get_on_call_number_from_file(oncall_file):
    phone_number = ''
    try:
        with open(oncall_file, 'r') as file_obj:
            phone_number = file_obj.readline(10)
    except IOError as e:
        logging.error("emailhandler.py :: IO error recieved while trying to read oncall.txt")
    except:
        logging.error("emailhandler.py :: Unexpected occured trying to read oncall.txt")
    return phone_number


def _on_call_request_email(mail):
    if isinstance(mail, email.message.Message):
        if str(mail['Subject']).upper() == "SLACKBOT WHO IS ON CALL":
            logging.debug("emailhandler.py :: _on_call_request_email found!")
            return True
    return False
