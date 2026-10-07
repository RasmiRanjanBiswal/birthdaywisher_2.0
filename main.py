import os
from datetime import datetime
import pandas as pd
import random
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone

MY_EMAIL = os.getenv("MY_EMAIL")
MY_PASSWORD = os.getenv("MY_PASSWORD")  # Gmail App Password

IST = timezone(timedelta(hours=5, minutes=30))
today_tuple = (datetime.now(IST).month, datetime.now(IST).day)

# Load birthdays CSV (with cc_mails and bcc_mails columns)
data = pd.read_csv("birthdays.csv")
data.columns = data.columns.str.strip()  # clean headers

# Find all people whose birthday is today
birthday_people = data[(data["month"] == today_tuple[0]) & (data["day"] == today_tuple[1])]

if not birthday_people.empty:
    with smtplib.SMTP("smtp.gmail.com", 587) as connection:
        connection.starttls()
        connection.login(MY_EMAIL, MY_PASSWORD)

        for _, person in birthday_people.iterrows():
            # ✅ Pick a random letter template
            letter_files = [f for f in os.listdir("letter_templates") if f.startswith("letter_") and f.endswith(".txt")]
            chosen_letter = random.choice(letter_files)
            with open(os.path.join("letter_templates", chosen_letter), encoding="utf-8") as letter_file:
                template_text = letter_file.read()

            # Replace placeholder with recipient’s name
            contents = template_text.replace("[NAME]", person["name"])
            contents_bold = f"<b>{contents}</b>"

            # ✅ Pick a random signature file
            signature_files = [f for f in os.listdir("signatures") if f.startswith("signature_") and f.endswith(".txt")]
            chosen_signature = random.choice(signature_files)
            with open(os.path.join("signatures", chosen_signature), encoding="utf-8") as sig_file:
                signature_text = sig_file.read()
                html_message = signature_text.replace(",", ",<br>")
                html_message_bold = f"<b>{html_message}</b>"

            # ✅ Pick a random image
            image_files = [f for f in os.listdir("attachments") if f.lower().endswith((".jpg", ".jpeg", ".png", ".avif", ".webp"))]
            chosen_image = random.choice(image_files) if image_files else None

            # Build the email
            msg = EmailMessage()
            msg["From"] = MY_EMAIL
            msg["To"] = person["email"]
            msg["Subject"] = "Happy Birthday!"

            # Add CC and BCC if present
            if pd.notna(person.get("cc_mails")):
                msg["Cc"] = person["cc_mails"]
            if pd.notna(person.get("bcc_mails")):
                msg["Bcc"] = person["bcc_mails"]

            # Plain text fallback
            plain_text = f"{contents}\n\n{signature_text}"
            msg.set_content(plain_text)

            # HTML version with inline image BEFORE signature
            html_content = f"""
            <html>
              <body style="font-family: Arial, sans-serif; font-size: 14px;">
                <pre style="white-space: pre-wrap; font-family: inherit;">{contents_bold}</pre>
                {"<img src='cid:birthday_img' alt='Birthday Image' style='width:800px; height:auto; margin-top:10px; margin-bottom:10px;'>" if chosen_image else ""}
                <p>{html_message_bold}</p>
              </body>
            </html>
            """
            msg.add_alternative(html_content, subtype="html")

            # Attach chosen image inline if available
            if chosen_image:
                with open(os.path.join("attachments", chosen_image), "rb") as f:
                    file_data = f.read()
                    msg.get_payload()[1].add_related(
                        file_data,
                        maintype="image",
                        subtype=chosen_image.split(".")[-1],
                        cid="birthday_img"
                    )

            # Send the email
            connection.send_message(msg)

            print(f"🎉 Birthday email sent to {person['name']} at {person['email']} "
                  f"(CC: {person.get('cc_mails', 'none')} | BCC: {person.get('bcc_mails', 'none')}) "
                  f"with template {chosen_letter}, image {chosen_image or 'no image'}, and signature {chosen_signature}")
