import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import os
import queue
from server import FileTransferServer
from client import FileTransferClient
from discovery import DeviceDiscovery

class MainWindow:
    def __init__(self, root, transfer_port=12345, discovery_port=12346):
        self.root = root
        self.root.title("LAN File Share Pro")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        self.root.configure(bg="#f0f0f0")
        
        # Custom colors and fonts
        self.colors = {
            "primary": "#4a6fa5",
            "secondary": "#166088",
            "background": "#f0f0f0",
            "text": "#333333",
            "highlight": "#4fc3f7"
        }
        self.fonts = {
            "title": ("Helvetica", 16, "bold"),
            "header": ("Helvetica", 12, "bold"),
            "normal": ("Helvetica", 10)
        }
        
        # Initialize services
        self.transfer_port = transfer_port
        self.discovery_port = discovery_port
        self.server = FileTransferServer(port=self.transfer_port)
        self.client = FileTransferClient()
        self.discovery = DeviceDiscovery(port=self.discovery_port)
        
        # Setup UI
        self.setup_ui()
        
        # Start services
        self.server.start()
        self.discovery.start()
        
        # Start processing messages
        self.process_messages()
        
        # Clean up on exit
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(
            header_frame,
            text="LAN File Share Pro",
            font=self.fonts["title"],
            foreground=self.colors["primary"]
        ).pack(side=tk.LEFT)
        
        # Device list section
        device_frame = ttk.LabelFrame(main_frame, text=" Available Devices ", padding=10)
        device_frame.pack(fill=tk.BOTH, pady=5)
        
        self.device_tree = ttk.Treeview(
            device_frame,
            columns=('ip', 'name'),
            show='headings',
            height=6,
            selectmode='browse'
        )
        self.device_tree.heading('ip', text='IP Address')
        self.device_tree.heading('name', text='Device Name')
        self.device_tree.column('ip', width=150, anchor=tk.W)
        self.device_tree.column('name', width=250, anchor=tk.W)
        
        scroll_y = ttk.Scrollbar(device_frame, orient=tk.VERTICAL, command=self.device_tree.yview)
        self.device_tree.configure(yscrollcommand=scroll_y.set)
        
        self.device_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.device_tree.bind('<<TreeviewSelect>>', self.on_device_select)
        
        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text=" File Selection ", padding=10)
        file_frame.pack(fill=tk.X, pady=10)
        
        btn_style = ttk.Style()
        btn_style.configure('Primary.TButton', foreground='white', background=self.colors["primary"])
        
        self.browse_btn = ttk.Button(
            file_frame,
            text="📁 Browse File",
            command=self.select_file,
            style='Primary.TButton'
        )
        self.browse_btn.pack(side=tk.LEFT, padx=5)
        
        self.file_label = ttk.Label(
            file_frame,
            text="No file selected",
            font=self.fonts["normal"],
            foreground=self.colors["text"],
            wraplength=400
        )
        self.file_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Progress section
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress = ttk.Progressbar(
            progress_frame,
            orient=tk.HORIZONTAL,
            length=100,
            mode='determinate',
            style='success.Horizontal.TProgressbar'
        )
        self.progress.pack(fill=tk.X, expand=True)
        
        self.progress_label = ttk.Label(
            progress_frame,
            text="Ready",
            font=self.fonts["normal"],
            foreground=self.colors["secondary"],
            anchor=tk.CENTER
        )
        self.progress_label.pack(fill=tk.X)
        
        # Transfer button
        self.send_btn = ttk.Button(
            main_frame,
            text="🚀 Send File",
            command=self.send_file,
            style='Primary.TButton',
            state=tk.DISABLED
        )
        self.send_btn.pack(pady=10)
        
        # Log section
        log_frame = ttk.LabelFrame(main_frame, text=" Activity Log ", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            wrap=tk.WORD,
            font=('Consolas', 9),
            padx=10,
            pady=10,
            bg='#ffffff',
            fg=self.colors["text"]
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready to connect...")
        ttk.Label(
            main_frame,
            textvariable=self.status_var,
            font=self.fonts["normal"],
            foreground=self.colors["secondary"],
            anchor=tk.W
        ).pack(fill=tk.X, pady=(5, 0))
    
    def select_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.file_path = file_path
            self.file_label.config(text=os.path.basename(file_path))
            self.update_send_button()
            self.add_log(f"📄 Selected file: {os.path.basename(file_path)}")
    
    def update_send_button(self):
        selection = self.device_tree.selection()
        if selection and hasattr(self, 'file_path'):
            self.send_btn.config(state=tk.NORMAL)
        else:
            self.send_btn.config(state=tk.DISABLED)
    
    def send_file(self):
        selection = self.device_tree.selection()
        if not selection or not hasattr(self, 'file_path'):
            return
            
        item = self.device_tree.item(selection[0])
        device_ip = item['values'][0]
        device_name = item['values'][1]
        
        self.add_log(f"📤 Sending file to {device_name} ({device_ip})...")
        self.progress_label.config(text="Sending file...")
        
        threading.Thread(
            target=self.client.send_file,
            args=(device_ip, self.transfer_port, self.file_path),
            daemon=True
        ).start()
    
    def add_log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.status_var.set(message)
    
    def on_device_select(self, event):
        selection = self.device_tree.selection()
        if selection:
            item = self.device_tree.item(selection[0])
            self.selected_device = item['values'][0]
            self.add_log(f"🔗 Selected device: {item['values'][1]} ({self.selected_device})")
            self.update_send_button()
    
    def process_messages(self):
        # Process discovery messages
        try:
            while True:
                msg_type, *args = self.discovery.message_queue.get_nowait()
                if msg_type == 'device':
                    ip, name = args
                    self.device_tree.insert('', tk.END, values=(ip, name))
                    self.add_log(f"🌐 Discovered device: {name} ({ip})")
                elif msg_type == 'log':
                    self.add_log(args[0])
        except queue.Empty:
            pass
        
        # Process server messages
        try:
            while True:
                msg_type, *args = self.server.message_queue.get_nowait()
                if msg_type == 'log':
                    self.add_log(f"📥 {args[0]}")
                elif msg_type == 'progress':
                    self.progress['value'] = args[0]
                    self.progress_label.config(text=f"Transfer: {args[0]}%")
        except queue.Empty:
            pass
        
        # Process client messages
        try:
            while True:
                msg_type, *args = self.client.message_queue.get_nowait()
                if msg_type == 'log':
                    self.add_log(f"📤 {args[0]}")
                elif msg_type == 'progress':
                    self.progress['value'] = args[0]
                    self.progress_label.config(text=f"Transfer: {args[0]}%")
        except queue.Empty:
            pass
        
        self.root.after(100, self.process_messages)
    
    def on_close(self):
        self.add_log("🛑 Shutting down services...")
        self.server.stop()
        self.discovery.stop()
        self.root.destroy()