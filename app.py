# app.py
import imaplib
import email
from email.header import decode_header
import os
import pandas as pd
import streamlit as st

# ---------------- Streamlit Page Config ----------------
st.set_page_config(
    page_title="Email Attachment Downloader",
    page_icon="📩",
    layout="wide"
)

st.title("📩 Email Attachment Downloader")
st.markdown("""
This app connects to your email, downloads attachments, and logs them in a CSV file.  
Use **Gmail App Password** if using Gmail.
""")

# ---------------- Streamlit Secrets ----------------
EMAIL_USER = st.secrets["EMAIL_USER"]
EMAIL_PASS = st.secrets["EMAIL_PASS"]
IMAP_SERVER = st.secrets.get("IMAP_SERVER", "imap.gmail.com")

# ---------------- Settings ----------------
SAVE_DIR = "attachments"
LOG_FILE = "logs.csv"

# Create folder if not exists
os.makedirs(SAVE_DIR, exist_ok=True)

# Load existing logs or create new
if not os.path.exists(LOG_FILE):
    logs_df = pd.DataFrame(columns=["Email_ID", "From", "Subject", "Attachment", "Saved_Path"])
    logs_df.to_csv(LOG_FILE, index=False)
else:
    logs_df = pd.read_csv(LOG_FILE)

# ---------------- Connect to Email ----------------
st.info("Connecting to email server...")
try:
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")
    st.success("✅ Connected to email server")
except Exception as e:
    st.error(f"Failed to connect: {e}")
    st.stop()

# ---------------- Fetch Emails ----------------
st.info("Fetching latest emails...")
status, messages = mail.search(None, "ALL")
messages = messages[0].split()

if not messages:
    st.warning("No emails found")
    st.stop()

# Process last N emails
N = st.sidebar.number_input("Number of latest emails to check", min_value=1, max_value=50, value=20)
processed_count = 0

for msg_id in messages[-N:]:
    status, msg_data = mail.fetch(msg_id, "(RFC822)")
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode(errors="ignore")
            from_ = msg.get("From")

            # Iterate through parts
            if msg.is_multipart():
                for part in msg.walk():
                    content_disposition = part.get("Content-Disposition")
                    if content_disposition and "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            filepath = os.path.join(SAVE_DIR, filename)
                            with open(filepath, "wb") as f:
                                f.write(part.get_payload(decode=True))
                            # Log attachment
                            logs_df = pd.concat([logs_df, pd.DataFrame([{
                                "Email_ID": msg_id.decode(),
                                "From": from_,
                                "Subject": subject,
                                "Attachment": filename,
                                "Saved_Path": filepath
                            }])], ignore_index=True)
                            processed_count += 1

# Save logs
logs_df.to_csv(LOG_FILE, index=False)

st.success(f"✅ Finished processing {processed_count} attachments")
st.write("### Logs")
st.dataframe(logs_df.tail(20))
