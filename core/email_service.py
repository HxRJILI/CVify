import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from core.config import Config

def send_verification_email(to_email: str, full_name: str, otp_code: str):
    """
    Sends a rich HTML verification email with the OTP code.
    This function blocks and should be called via a Worker thread.
    """
    
    # If no SMTP credentials are provided, we simulate success for local dev testing
    # In a real app this would just fail, but for a showcase, printing the OTP is quite helpful if .env is not setup.
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD or Config.SMTP_USER == "your_email@gmail.com":
        print(f"*** SIMULATED EMAIL (No SMTP configured) ***")
        print(f"To: {to_email}")
        print(f"OTP: {otp_code}")
        print(f"********************************************")
        return True

    sender_email = Config.FROM_EMAIL or Config.SMTP_USER
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your CVify Verification Code"
    msg["From"] = f"CVify <{sender_email}>"
    msg["To"] = to_email

    text = f"""
    Hi {full_name},
    
    Your verification code is: {otp_code}
    
    This code expires in 15 minutes.
    
    The CVify Team
    """
    
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333; padding: 40px; margin: 0;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
          <h2 style="color: #6C63FF; margin-top: 0; text-align: center;">CVify</h2>
          <p style="font-size: 16px;">Hi {full_name},</p>
          <p style="font-size: 16px;">Please use the verification code below to complete your registration:</p>
          
          <div style="background-color: #f0f0f8; padding: 20px; text-align: center; border-radius: 8px; margin: 30px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #1a1a24;">{otp_code}</span>
          </div>
          
          <p style="font-size: 14px; color: #666; text-align: center;">This code will expire in 15 minutes.</p>
          
          <hr style="border: none; border-top: 1px solid #eee; margin: 40px 0 20px 0;">
          <p style="font-size: 12px; color: #999; text-align: center;">If you didn't request this email, you can safely ignore it.</p>
        </div>
      </body>
    </html>
    """

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    msg.attach(part1)
    msg.attach(part2)

    context = ssl.create_default_context()
    
    with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
        server.sendmail(sender_email, to_email, msg.as_string())
        
    return True
