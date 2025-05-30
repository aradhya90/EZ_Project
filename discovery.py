import socket
import threading
import time
from queue import Queue

class DeviceDiscovery:
    def __init__(self, port=12346):
        self.port = port
        self.running = False
        self.devices = {}
        self.message_queue = Queue()
        
    def start(self):
        self.running = True
        threading.Thread(target=self.run_discovery, daemon=True).start()
        
    def stop(self):
        self.running = False
        
    def run_discovery(self):
        hostname = socket.gethostname()
        local_ip = self.get_local_ip()
        broadcast_ip = self.get_broadcast_ip(local_ip)
        
        # Broadcast listener
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.settimeout(1)
            s.bind(('', self.port))
            
            # Broadcast sender
            broadcast_msg = f"DISCOVER:{hostname}:{local_ip}"
            
            while self.running:
                try:
                    # Send broadcast
                    s.sendto(broadcast_msg.encode(), (broadcast_ip, self.port))
                    
                    # Listen for responses
                    try:
                        data, addr = s.recvfrom(1024)
                        if data.startswith(b"DISCOVER:"):
                            parts = data.decode().split(':')
                            if len(parts) == 3 and parts[2] != local_ip:
                                device_ip = parts[2]
                                device_name = parts[1]
                                if device_ip not in self.devices:
                                    self.devices[device_ip] = device_name
                                    self.message_queue.put(('device', device_ip, device_name))
                    except socket.timeout:
                        pass
                    
                    time.sleep(2)
                except Exception as e:
                    self.message_queue.put(('log', f"Discovery error: {str(e)}"))
    
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def get_broadcast_ip(self, ip):
        if ip == "127.0.0.1":
            return "127.255.255.255"
        parts = ip.split('.')
        parts[-1] = '255'
        return '.'.join(parts)