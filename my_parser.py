import mailparser
import email
import re


def get_body_string(mail):
    if isinstance(mail, email.message.Message):
        return mailparser.parse_from_string(mail.as_string()).body


def get_summary(mail):
    body_string = get_body_string(mail)
    # Because of how the subject is hard formatted,
    # First instance of 'Summary' is what we always be looking for
    summary_match = re.search(r"Summary[\s,\n]*", body_string)
    if summary_match:
        end = body_string.find("\n", summary_match.end())
        if end > summary_match.end():
            return body_string[summary_match.end():end]
        else:
            return "Summary not found correctly"
    else:
        return "Summary not found"


def get_cid(mail):
    # \n\n\nContact Information
    # We'll just search for 2 new lines before Contact Information and then whitespace followed by Customer
    body_string = get_body_string(mail)
    ci = re.search(r"Contact Information[\s,\n]*Customer", body_string)
    if ci:
        ci_string = body_string[ci.end():]
        company_id = re.search(r"Cost Center[\s,\n]*", ci_string)
        if company_id:
            return ci_string[company_id.end():company_id.end() + 3]
    else:
        return "Center ID Not Found"
