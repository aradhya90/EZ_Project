import socket
import os
from queue import Queue

class FileTransferClient:
    def __init__(self, buffer_size=4096):
        self.buffer_size = buffer_size
        self.message_queue = Queue()
        
    def send_file(self, host, port, file_path):
        try:
            filename = os.path.basename(file_path)
            filesize = os.path.getsize(file_path)
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                
                # Send metadata
                s.sendall(f"FILE:{filename}:{filesize}".encode())
                self.message_queue.put(('log', f"Sending {filename} to {host}"))
                
                # Send file data
                sent_bytes = 0
                with open(file_path, 'rb') as f:
                    while True:
                        bytes_read = f.read(self.buffer_size)
                        if not bytes_read:
                            break
                        s.sendall(bytes_read)
                        sent_bytes += len(bytes_read)
                        progress = int((sent_bytes / filesize) * 100)
                        self.message_queue.put(('progress', progress))
                
                self.message_queue.put(('log', "File sent successfully"))
                
        except Exception as e:
            self.message_queue.put(('log', f"Error: {str(e)}"))