#!/usr/bin/env python
# -*- coding: utf-8 -*-

import smtplib

from email.mime.text import MIMEText

COMMASPACE = ', '

def send_mail(recipients, sender, subject, msg):
    msg = MIMEText(msg)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = COMMASPACE.join(recipients)

    server = smtplib.SMTP('localhost')
    server.sendmail(sender, recipients, msg.as_string())
    server.quit()
