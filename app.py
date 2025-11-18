# app.py
import streamlit as st
import pandas as pd
import os
import imaplib
import email
from email.header import decode_header

# ---------------- Configuration ----------------
EMAIL_USER = "your_email@gmail.com"
EMAIL_PASS = "your_app_password"  # Use app password if Gmail
IMAP_SERVER = "imap.gmail.com"
SAVE_DIR = "attachments"
LOG_FILE = "logs.csv"

os.makedirs(SAVE_DIR, exist_ok=True)

# ---------------- Streamlit App ----------------
st.set_page_config(page_title="Email Attachment Organizer", layout="wide")
st.title("📧 Smart Email Attachment Organizer")

st.markdown("""
Fetch attachments from your inbox, track downloads, and visualize statistics.
""")

# --- Sidebar ---
st.sidebar.header("Controls")
run_fetch = st.sidebar.button("Fetch Latest Emails")
file_types = st.sidebar.multiselect(
    "Filter by File Type",
    options=["All", "PDF", "Image", "Excel", "Other"],
    default=["All"]
)

# Initialize logs CSV if not exists
if not os.path.exists(LOG_FILE):
    pd.DataFrame(columns=["Email_ID", "From", "Subject", "Attachment", "Saved_Path"]).to_csv(LOG_FILE, index=False)

logs = pd.read_csv(LOG_FILE)

# ---------------- Fetch Emails Function ----------------
def fetch_emails(last_n=20):
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")

    status, messages = mail.search(None, "ALL")
    messages = messages[0].split()

    new_logs = []

    for msg_id in messages[-last_n:]:
        status, msg_data = mail.fetch(msg_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode(errors="ignore")
                from_ = msg.get("From")

                if msg.is_multipart():
                    for part in msg.walk():
                        content_disposition = part.get("Content-Disposition")
                        if content_disposition and "attachment" in content_disposition:
                            filename = part.get_filename()
                            if filename:
                                filepath = os.path.join(SAVE_DIR, filename)
                                with open(filepath, "wb") as f:
                                    f.write(part.get_payload(decode=True))
                                new_logs.append({
                                    "Email_ID": msg_id.decode(),
                                    "From": from_,
                                    "Subject": subject,
                                    "Attachment": filename,
                                    "Saved_Path": filepath
                                })
    return new_logs

# ---------------- Run Fetch ----------------
if run_fetch:
    st.info("Fetching emails...")
    new_entries = fetch_emails()
    if new_entries:
        logs = pd.concat([logs, pd.DataFrame(new_entries)], ignore_index=True)
        logs.to_csv(LOG_FILE, index=False)
        st.success(f"✅ Fetched {len(new_entries)} attachments")
    else:
        st.warning("No new attachments found.")

# ---------------- Apply Filters ----------------
filtered_logs = logs.copy()

if "All" not in file_types:
    ext_map = {
        "PDF": ".pdf",
        "Image": (".png", ".jpg", ".jpeg", ".gif"),
        "Excel": (".xls", ".xlsx")
    }
    allowed_exts = []
    for ft in file_types:
        allowed_exts.extend(ext_map.get(ft, ()))
    filtered_logs = filtered_logs[filtered_logs['Attachment'].str.lower().str.endswith(tuple(allowed_exts))]

# ---------------- Tabs ----------------
tab1, tab2, tab3 = st.tabs(["Latest Downloads", "Stats & Charts", "Download Logs"])

# --- Tab 1: Latest Downloads ---
with tab1:
    st.subheader("Latest Attachments")
    st.dataframe(filtered_logs.tail(20))

# --- Tab 2: Stats & Charts ---
with tab2:
    st.subheader("Files by Sender")
    st.bar_chart(filtered_logs['From'].value_counts())

    st.subheader("Files by Type")
    filtered_logs['File_Type'] = filtered_logs['Attachment'].apply(lambda x: os.path.splitext(x)[1])
    st.bar_chart(filtered_logs['File_Type'].value_counts())

# --- Tab 3: Download Logs ---
with tab3:
    st.subheader("Download Logs CSV")
    st.download_button(
        label="Download Logs",
        data=filtered_logs.to_csv(index=False),
        file_name="logs.csv",
        mime="text/csv"
    )
