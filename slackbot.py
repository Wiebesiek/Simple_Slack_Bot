import win32serviceutil
import win32service
import win32event
import servicemanager
import logging
import socket
import time
import emailhandler
import mysecrets
import slackhandler
from logging.handlers import RotatingFileHandler


# https://stackoverflow.com/questions/13466053/all-python-windows-service-can-not-starterror-1053
class AppServerSvc (win32serviceutil.ServiceFramework):
    _svc_name_ = "SlackNotifyBot"
    _svc_display_name_ = "Slack Bot"

    def __init__(self, args):
        self.eh = emailhandler.emailhandler()
        self.sh = slackhandler.SlackHandler()

        # set up current timestamp for newest timestamp
        self.sh.get_new_messages()

        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = True
        socket.setdefaulttimeout(60)

    # can take 60 seconds to kill
    def SvcStop(self):
        self.is_running = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.is_running = True
        self.main()

    def main(self):
        # set up logging
        logging.basicConfig(format='%(asctime)s %(message)s',
                            filename=mysecrets.log_file_location,
                            level=logging.DEBUG)
        logger = logging.getLogger()
        logger.debug('slackbot.py:: Service start')

        # email account is only for this bot
        try:
            self.eh.read_all_emails()
        except:
            logger.error("slackbot.py:: read_all_emails was unsuccessful")

        while self.is_running:
            # We'll leave this excessive logging on, for now
            logger.debug('slackbot.py:: Entering while loop')
            time.sleep(60)

            # check emails
            emails = self.eh.get_emails()
            self.eh.process_emails(emails)

            # check slack channel
            # todo: Need to break it down on a per message basis not a 60 second basis
            # this way we can put a specific message on the send sms
            messages = self.sh.get_new_messages()
            for m in messages:



if __name__ == '__main__':
    # set up logging
    rfh = logging.handlers.RotatingFileHandler(
        filename=mysecrets.log_file_location,
        mode='a',
        maxBytes=10000,
        backupCount=3
    )
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(message)s',
        handlers=[rfh]
    )
    logger = logging.getLogger()
    win32serviceutil.HandleCommandLine(AppServerSvc)
