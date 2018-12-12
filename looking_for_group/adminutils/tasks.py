from anymail.message import AnymailMessage
from markdown import markdown
from notifications.signals import notify


def send_mass_notifcation(current_site, message, recipient_list):
    for user in recipient_list:
        notify.send(current_site, recipient=user, verb=message)


def send_mass_email(subject, body_plain, recipient_list):
    mail_batch = []
    recip_count = recipient_list.count()
    cur_index = 0
    while recip_count > 0:
        # split the list into chunks of 1000 or less and iterate through those
        mail_batch.append(recipient_list[cur_index:999])
        recip_count -= 999
        cur_index += 999
    if mail_batch:
        for recip_list in mail_batch:
            msg = AnymailMessage(subject=subject, body=body_plain, to=[u.email for u in recip_list])
            msg.attach_alternative("<html>{}</html>".format(markdown(body_plain)), "text/html")
            merge_data = {}
            for u in recip_list:
                if u.display_name:
                    merge_data[u.email] = {'NAME': u.display_name}
                else:
                    merge_data[u.email] = {'NAME': u.username}
            msg.merge_data = merge_data
            msg.send()
