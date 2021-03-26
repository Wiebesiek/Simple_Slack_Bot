import mailparser
import email


def get_body_string(mail: email.message.Message):
    if isinstance(mail, email.message.Message):
        return mailparser.parse_from_string(mail.as_string()).body


def get_summary(mail: email.message.Message):
    body_string = get_body_string(mail)
    # \n\nSummary\n\n    is the first tag
    # ^ this tag may be unreliable
    # \nSummary         Internet issues
    # ^ This was the tag on the most recent ticket.
    start = body_string.find("\n\nSummary\n\n") + 11
    if start < 11:
        return "Summary Not Found"
    # \n\nTarget Resolution is the end tag
    end = body_string.find("\n\nTarget Resolution")
    return body_string[start:end]
