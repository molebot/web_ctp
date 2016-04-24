import smtplib
from email.mime.text import MIMEText
#from email.mime.multipart import MIMEMultipart
from log import logit

from_ = ''
pswd = ''
host = ''
port = 465

def sendmail(to_,sub_,main_="molebot.com"):
    server = smtplib.SMTP_SSL()
    logit(str(server.connect(host,port)))
    logit((server.login(from_,pswd)))
    msg = MIMEText(main_)
    msg['From'] = from_
    msg['To'] = to_
    msg['Subject'] = sub_
    logit(str(server.sendmail(from_,to_,msg.as_string())))
    logit('qqmail ok')
    server.quit()
    
def alertmail(sub_,main_="from molebot.com"):
    sendmail('botbot@189.cn',sub_,main_)

#alertmail('begin','ok')