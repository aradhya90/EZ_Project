import socket
import os
import threading
from queue import Queue

class FileTransferServer:
    def __init__(self, port=12345, buffer_size=4096):
        self.port = port
        self.buffer_size = buffer_size
        self.running = False
        self.message_queue = Queue()
        
    def start(self):
        self.running = True
        threading.Thread(target=self.run_server, daemon=True).start()
        
    def stop(self):
        self.running = False
        
    def run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', self.port))
            s.listen()
            
            while self.running:
                try:
                    conn, addr = s.accept()
                    threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()
                except:
                    break
    
    def handle_client(self, conn, addr):
        try:
            # Receive metadata
            data = conn.recv(self.buffer_size).decode()
            if not data.startswith("FILE:"):
                return
                
            _, filename, filesize = data.split(':', 2)
            filesize = int(filesize)
            
            self.message_queue.put(('log', f"Receiving {filename} from {addr[0]}"))
            
            # Receive file data
            save_path = os.path.join('received_files', filename)
            os.makedirs('received_files', exist_ok=True)
            
            received_bytes = 0
            with open(save_path, 'wb') as f:
                while received_bytes < filesize:
                    data = conn.recv(min(self.buffer_size, filesize - received_bytes))
                    if not data:
                        break
                    f.write(data)
                    received_bytes += len(data)
                    progress = int((received_bytes / filesize) * 100)
                    self.message_queue.put(('progress', progress))
            
            self.message_queue.put(('log', f"File received: {filename}"))
            
        except Exception as e:
            self.message_queue.put(('log', f"Error: {str(e)}"))
        finally:
            conn.close()