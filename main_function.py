import os
import mimetypes
from datetime import datetime
import pandas as pd
import random
import smtplib
from email.message import EmailMessage

# ---------- Configuration ----------
MY_EMAIL = os.getenv("MY_EMAIL")
MY_PASSWORD = os.getenv("MY_PASSWORD")
LETTER_DIR = "letter_templates"
SIGNATURE_DIR = "signatures"
ATTACH_DIR = "attachments"
CSV_FILE = "birthdays.csv"
SMTP_HOST = "smtp.gmail.com"
SMTP_SSL_PORT = 465
SMTP_STARTTLS_PORT = 587
# -----------------------------------

def load_file_list(folder, prefix=None, suffix=None):
    try:
        files = os.listdir(folder)
    except FileNotFoundError:
        return []
    if prefix:
        files = [f for f in files if f.startswith(prefix)]
    if suffix:
        files = [f for f in files if f.endswith(suffix)]
    return files

def parse_address_field(field_value):
    """Return list of addresses from a CSV cell that may contain comma/semicolon separated addresses."""
    if pd.isna(field_value):
        return []
    if not isinstance(field_value, str):
        return []
    parts = [p.strip() for p in field_value.replace(";", ",").split(",") if p.strip()]
    return parts

def choose_random_or_none(lst):
    return random.choice(lst) if lst else None

def attach_inline_image(msg, html_part_index, image_path, cid="birthday_img"):
    ctype, encoding = mimetypes.guess_type(image_path)
    if ctype is None:
        maintype, subtype = "application", "octet-stream"
    else:
        maintype, subtype = ctype.split("/", 1)
    with open(image_path, "rb") as f:
        data = f.read()
    # add_related on the html alternative part
    msg.get_payload()[html_part_index].add_related(data, maintype=maintype, subtype=subtype, cid=cid)

def send_with_fallback(msg, recipients):
    """Try SMTP SSL first, then STARTTLS fallback. Returns True on success, False otherwise."""
    # Try SSL
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_SSL_PORT, timeout=30) as conn:
            conn.login(MY_EMAIL, MY_PASSWORD)
            conn.send_message(msg, from_addr=MY_EMAIL, to_addrs=recipients)
        return True
    except Exception as e_ssl:
        print(f"[WARN] SMTP_SSL failed: {e_ssl}. Trying STARTTLS...")
    # Fallback to STARTTLS
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_STARTTLS_PORT, timeout=30) as conn:
            conn.ehlo()
            conn.starttls()
            conn.ehlo()
            conn.login(MY_EMAIL, MY_PASSWORD)
            conn.send_message(msg, from_addr=MY_EMAIL, to_addrs=recipients)
        return True
    except Exception as e_tls:
        print(f"[ERROR] STARTTLS failed: {e_tls}")
        return False

def main():
    today = (datetime.now().month, datetime.now().day)

    # Load CSV and normalize headers
    try:
        data = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print(f"[ERROR] CSV file not found: {CSV_FILE}")
        return
    data.columns = data.columns.str.strip()

    # Validate required columns
    required = {"name", "email", "month", "day"}
    if not required.issubset(set(data.columns)):
        print(f"[ERROR] CSV missing required columns. Found: {list(data.columns)}")
        return

    # Filter today's birthdays
    birthday_people = data[(data["month"] == today[0]) & (data["day"] == today[1])]
    if birthday_people.empty:
        print("No birthdays today.")
        return

    # Cache available files
    letter_files = load_file_list(LETTER_DIR, prefix="letter_", suffix=".txt")
    signature_files = load_file_list(SIGNATURE_DIR, prefix="signature_", suffix=".txt")
    image_files = load_file_list(ATTACH_DIR)
    image_files = [f for f in image_files if f.lower().endswith((".jpg", ".jpeg", ".png", ".avif", ".webp"))]

    if not letter_files:
        print(f"[WARN] No letter templates found in {LETTER_DIR}.")
    if not signature_files:
        print(f"[WARN] No signature files found in {SIGNATURE_DIR}.")

    # Process each birthday person
    for _, person in birthday_people.iterrows():
        try:
            # Choose random assets
            chosen_letter = choose_random_or_none(letter_files)
            chosen_signature = choose_random_or_none(signature_files)
            chosen_image = choose_random_or_none(image_files)

            # Read template and signature text
            template_text = ""
            if chosen_letter:
                with open(os.path.join(LETTER_DIR, chosen_letter), encoding="utf-8") as f:
                    template_text = f.read()
            signature_text = ""
            if chosen_signature:
                with open(os.path.join(SIGNATURE_DIR, chosen_signature), encoding="utf-8") as f:
                    signature_text = f.read()

            # Personalize
            contents = template_text.replace("[NAME]", person["name"]) if template_text else f"Happy Birthday, {person['name']}!"
            html_contents = f"<b>{contents}</b>"
            html_signature = f"<b>{signature_text.replace(',', ',<br>')}</b>" if signature_text else ""

            # Build message
            msg = EmailMessage()
            msg["From"] = MY_EMAIL
            msg["To"] = person["email"]
            msg["Subject"] = "Happy Birthday!"

            # Parse CC/BCC fields (support multiple addresses separated by comma or semicolon)
            cc_list = parse_address_field(person.get("cc_mails", ""))
            bcc_list = parse_address_field(person.get("bcc_mails", ""))

            if cc_list:
                msg["Cc"] = ", ".join(cc_list)
            if bcc_list:
                msg["Bcc"] = ", ".join(bcc_list)

            # Plain text fallback
            plain_text = f"{contents}\n\n{signature_text}"
            msg.set_content(plain_text)

            # HTML alternative
            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; font-size: 14px;">
                <pre style="white-space: pre-wrap; font-family: inherit;">{html_contents}</pre>
                {"<img src='cid:birthday_img' alt='Birthday Image' style='max-width:800px; height:auto; margin-top:10px; margin-bottom:10px;'>" if chosen_image else ""}
                <p>{html_signature}</p>
              </body>
            </html>
            """
            msg.add_alternative(html_body, subtype="html")

            # Attach inline image if available
            if chosen_image:
                image_path = os.path.join(ATTACH_DIR, chosen_image)
                try:
                    # html part is the second payload (index 1) after plain text
                    attach_inline_image(msg, html_part_index=1, image_path=image_path, cid="birthday_img")
                except Exception as e_img:
                    print(f"[WARN] Failed to attach image {chosen_image}: {e_img}")

            # Build final recipient list (To + Cc + Bcc)
            recipients = [person["email"]] + cc_list + bcc_list

            # Send message with fallback
            success = send_with_fallback(msg, recipients)
            if success:
                print(f"🎉 Sent to {person['name']} <{person['email']}> (CC: {cc_list or 'none'} | BCC: {bcc_list or 'none'}) "
                      f"template={chosen_letter or 'none'} signature={chosen_signature or 'none'} image={chosen_image or 'none'}")
            else:
                print(f"[ERROR] Failed to send to {person['name']} <{person['email']}>")

        except Exception as e:
            print(f"[ERROR] Unexpected error for {person.get('name', 'unknown')}: {e}")

if __name__ == "__main__":
    main()
