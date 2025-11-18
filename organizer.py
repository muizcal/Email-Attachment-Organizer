import imaplib
import email
from email.header import decode_header
import os
import pandas as pd

# ---------------- Configuration ----------------
EMAIL_USER = "your_email@gmail.com"
EMAIL_PASS = "your_app_password"  # Use app password if Gmail
IMAP_SERVER = "imap.gmail.com"
SAVE_DIR = "attachments"

# Ensure attachment folder exists
os.makedirs(SAVE_DIR, exist_ok=True)

# ---------------- Connect to Email ----------------
mail = imaplib.IMAP4_SSL(IMAP_SERVER)
mail.login(EMAIL_USER, EMAIL_PASS)
mail.select("inbox")

# Search for all emails
status, messages = mail.search(None, "ALL")
messages = messages[0].split()

# CSV log
log_file = "logs.csv"
if not os.path.exists(log_file):
    pd.DataFrame(columns=["Email_ID", "From", "Subject", "Attachment", "Saved_Path"]).to_csv(log_file, index=False)

logs = pd.read_csv(log_file)

# ---------------- Process Emails ----------------
for msg_id in messages[-20:]:  # last 20 emails
    status, msg_data = mail.fetch(msg_id, "(RFC822)")
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()
            from_ = msg.get("From")

            # Iterate over email parts
            if msg.is_multipart():
                for part in msg.walk():
                    content_disposition = part.get("Content-Disposition")
                    if content_disposition and "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            filepath = os.path.join(SAVE_DIR, filename)
                            with open(filepath, "wb") as f:
                                f.write(part.get_payload(decode=True))
                            # Log to CSV
                            logs = logs.append({
                                "Email_ID": msg_id.decode(),
                                "From": from_,
                                "Subject": subject,
                                "Attachment": filename,
                                "Saved_Path": filepath
                            }, ignore_index=True)

# Save logs
logs.to_csv(log_file, index=False)
print("✅ Finished processing attachments")
