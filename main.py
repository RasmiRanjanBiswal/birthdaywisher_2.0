import os
from datetime import datetime
import pandas as pd
import random
import smtplib
from email.message import EmailMessage

MY_EMAIL = "rinkubiswal.hbk@gmail.com"
MY_PASSWORD = "aeif mvmk kglu rexf"  # Gmail App Password

today_tuple = (datetime.now().month, datetime.now().day)

# Load birthdays
data = pd.read_csv("birthdays.csv")

# Find all people whose birthday is today
birthday_people = data[(data["month"] == today_tuple[0]) & (data["day"] == today_tuple[1])]

if not birthday_people.empty:
    with smtplib.SMTP("smtp.gmail.com", 587) as connection:
        connection.starttls()
        connection.login(MY_EMAIL, MY_PASSWORD)

        for _, person in birthday_people.iterrows():
            # Pick a random letter template
            file_path = f"letter_templates/letter_{random.randint(1, 3)}.txt"
            with open(file_path, encoding="utf-8") as letter_file:
                template_text = letter_file.read()

            # Replace placeholder with recipient’s name
            contents = template_text.replace("[NAME]", person["name"])

            # Build the email
            msg = EmailMessage()
            msg["From"] = MY_EMAIL
            msg["To"] = person["email"]
            msg["Subject"] = "Happy Birthday!"

            # Plain text fallback
            msg.set_content(contents)

            # Pick a random image from attachments folder
            image_files = [f for f in os.listdir("attachments") if f.lower().endswith((".jpg", ".jpeg", ".png", ".avif", ".webp"))]
            chosen_image = random.choice(image_files)

            # HTML version with inline image
            html_content = f"""
            <html>
              <body style="font-family: Arial, sans-serif; font-size: 14px;">
                <pre style="font-family: inherit; white-space: pre-wrap;">
{contents}

Lots of love,
Rinku
                </pre>
                <img src="cid:birthday_img" alt="Birthday Image" style="width:600px; height:auto;">
              </body>
            </html>
            """
            msg.add_alternative(html_content, subtype="html")

            # Attach chosen image inline
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

            print(f"🎉 Birthday email sent to {person['name']} at {person['email']} with image {chosen_image}")
