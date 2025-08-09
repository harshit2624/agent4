import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import threading
import time

class EmailNotifier:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = "croscrowteam@gmail.com"
        self.sender_password = "xhxh tyhz zvzl losx"
        self.recipient_email = "harshitvj24@gmail.com"
    
    def send_email(self, subject, body):
        """Send email notification"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.sender_email, self.recipient_email, text)
            server.quit()
            
            print(f"✅ Email sent: {subject}")
            return True
            
        except Exception as e:
            print(f"❌ Email failed: {str(e)}")
            return False
    
    def send_scheduled_notification(self, person, meeting_time):
        """Send email when meeting is scheduled"""
        subject = f"Meeting Scheduled - {person}"
        body = f"""
Hello,

A new meeting has been scheduled:

📅 Person: {person}
🕐 Time: {meeting_time.strftime('%I:%M %p, %d %b %Y')}
📍 Status: Confirmed

Please be ready for the meeting at the scheduled time.

Best regards,
Meeting Scheduler Bot
"""
        return self.send_email(subject, body)
    
    def send_reminder_notification(self, person, meeting_time):
        """Send reminder 10 minutes before meeting"""
        subject = f"Meeting Reminder - {person} in 10 minutes"
        body = f"""
Hello,

This is a reminder that you have a meeting in 10 minutes:

📅 Person: {person}
🕐 Time: {meeting_time.strftime('%I:%M %p, %d %b %Y')}
⏰ Remaining: 10 minutes

Please prepare for your meeting.

Best regards,
Meeting Scheduler Bot
"""
        return self.send_email(subject, body)
    
    def schedule_reminder(self, person, meeting_time):
        """Schedule reminder email 10 minutes before meeting"""
        reminder_time = meeting_time - timedelta(minutes=10)
        
        def send_reminder():
            # Calculate delay until reminder
            now = datetime.now()
            delay = (reminder_time - now).total_seconds()
            
            if delay > 0:
                time.sleep(delay)
                self.send_reminder_notification(person, meeting_time)
        
        # Start reminder thread
        reminder_thread = threading.Thread(target=send_reminder)
        reminder_thread.daemon = True
        reminder_thread.start()
        print(f"⏰ Reminder scheduled for {reminder_time.strftime('%I:%M %p')}")

    def send_custom_notification(self, to_email, subject, body):
        """Send a custom email notification to any recipient"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, to_email, msg.as_string())
            server.quit()
            print(f"✅ Custom email sent: {subject} to {to_email}")
            return True
        except Exception as e:
            print(f"❌ Custom email failed: {str(e)}")
            return False
