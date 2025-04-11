import hid
import time
import threading
import tkinter as tk
from tkinter import Canvas
import numpy as np
from PIL import Image, ImageTk
import queue

class HIDListener:
    def __init__(self, vendor_id=0x8089, product_id=0x0009, usage_page=0xFF12):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.usage_page = usage_page
        self.device = None
        self.running = False
        self.frame_buffer = np.zeros((80, 160), dtype=np.uint16)
        self.raw_buffer = np.zeros(160 * 80, dtype=np.uint16)
        self.last_update_time = time.time()
        self.fps_counter = 0
        self.fps = 0
        self.frame_queue = queue.Queue(maxsize=2)  # Buffer for frames between threads
        self.setup_gui()
        
    def find_and_open_device(self):
        """Find and open the specified HID device."""
        devices = hid.enumerate(self.vendor_id, self.product_id)
        
        if not devices:
            print(f"No devices found with VID={hex(self.vendor_id)}, PID={hex(self.product_id)}")
            return False
            
        device_path = None
        for device in devices:
            if device['usage_page'] == self.usage_page:
                device_path = device['path']
                break
                
        if not device_path:
            print(f"Found devices, but none with usage_page={hex(self.usage_page)}")
            return False
            
        try:
            self.device = hid.device()
            self.device.open_path(device_path)
            self.device.set_nonblocking(1)  # Set non-blocking mode for faster reads
            print(f"Connected to {self.device.get_manufacturer_string()} {self.device.get_product_string()}")
            return True
        except Exception as e:
            print(f"Failed to open device: {e}")
            return False
    
    def setup_gui(self):
        """Create a simple GUI to display the device output."""
        self.root = tk.Tk()
        self.root.title("SayoDevice HID Viewer")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Create canvas with 4x scaling
        self.width, self.height = 160*4, 80*4
        self.canvas = Canvas(self.root, width=self.width, height=self.height, bg="black")
        self.canvas.pack()
        
        # Create RGB array for faster image generation
        self.image_data = np.zeros((80, 160, 3), dtype=np.uint8)
        
        # Create PIL image for faster rendering
        self.pil_image = Image.new('RGB', (160, 80))
        self.photo_image = ImageTk.PhotoImage(self.pil_image)
        self.canvas_image = self.canvas.create_image(0, 0, image=self.photo_image, anchor=tk.NW)
        
        # Create FPS display
        self.fps_display = self.canvas.create_text(10, 10, text="FPS: 0", fill="white", anchor=tk.NW)
        
        # Pre-allocate memory for packets and responses
        self.packets = []
        self.read_buffer = bytes(1024)  # Pre-allocate buffer for reads
        
        # Build optimized packet structures
        chunk_size = 0x3F4  # Original chunk size
        total_size = 160 * 80 * 2
        
        # Create more optimized chunks for faster retrieval
        num_chunks = (total_size + chunk_size - 1) // chunk_size
        
        for i in range(num_chunks):
            offset = i * chunk_size
            
            # Create packet
            packet = bytearray([0x22, 0x03, 0x00, 0x00, 0x08, 0x00, 0x25, 0x00, 0x00, 0x00, 0x00, 0x00])
            packet.extend([0] * (1024 - len(packet)))  # Pad to 1024 bytes
            
            # Update packet offset
            packet[8] = offset & 0xFF
            packet[9] = (offset >> 8) & 0xFF
            packet[10] = (offset >> 16) & 0xFF
            packet[11] = (offset >> 24) & 0xFF
            
            self.packets.append(packet)
            
        # Create color lookup table for RGB565 to RGB888 conversion (much faster)
        self.r_lut = np.zeros(32, dtype=np.uint8)
        self.g_lut = np.zeros(64, dtype=np.uint8)
        self.b_lut = np.zeros(32, dtype=np.uint8)
        
        for i in range(32):
            self.r_lut[i] = (i << 3) | (i >> 2)
        for i in range(64):
            self.g_lut[i] = (i << 2) | (i >> 4)
        for i in range(32):
            self.b_lut[i] = (i << 3) | (i >> 2)
        
    def on_close(self):
        """Handle window close event."""
        self.running = False
        if self.device:
            self.device.close()
        self.root.destroy()
        
    def update_display(self):
        """Update the display with current frame buffer data."""
        try:
            # Try to get a new frame if available
            new_frame = self.frame_queue.get_nowait()
            self.frame_buffer = new_frame
            self.frame_queue.task_done()
        except queue.Empty:
            pass  # Use last frame if no new one is available
            
        # Use vectorized operations for faster processing
        r = self.r_lut[(self.frame_buffer >> 11) & 0x1F]
        g = self.g_lut[(self.frame_buffer >> 5) & 0x3F]
        b = self.b_lut[self.frame_buffer & 0x1F]
        
        # Reshape to 80x160x3
        rgb_data = np.stack([r, g, b], axis=2)
        
        # Update the PIL image and PhotoImage
        self.pil_image = Image.fromarray(rgb_data, mode='RGB')
        self.pil_image = self.pil_image.resize((self.width, self.height), Image.NEAREST)
        self.photo_image = ImageTk.PhotoImage(self.pil_image)
        self.canvas.itemconfig(self.canvas_image, image=self.photo_image)
        
        # Update FPS counter
        self.fps_counter += 1
        current_time = time.time()
        if current_time - self.last_update_time >= 1.0:
            self.fps = self.fps_counter
            self.canvas.itemconfig(self.fps_display, text=f"FPS: {self.fps}")
            self.fps_counter = 0
            self.last_update_time = current_time
    
    def update_packet_checksums(self):
        """Pre-calculate checksums for all packets."""
        for packet in self.packets:
            # Calculate checksum
            packet[2] = 0
            packet[3] = 0
            checksum = 0
            for j in range(0, len(packet), 2):
                checksum += (packet[j] | (packet[j+1] << 8))
            packet[2] = checksum & 0xFF
            packet[3] = (checksum >> 8) & 0xFF
    
    def read_frame_buffer_optimized(self):
        """Optimized reading from the HID device."""
        if not self.device:
            return
        
        # Update checksums for packets (only once per batch)
        self.update_packet_checksums()
        
        # Send all packets in batch
        for packet in self.packets:
            try:
                self.device.write(bytes(packet))
            except Exception as e:
                print(f"Failed to write to device: {e}")
                return
        
        # Create a new buffer for this frame
        new_raw_buffer = np.zeros(160 * 80, dtype=np.uint16)
        
        # Read all responses with minimal delay
        offset = 0
        start_read_time = time.time()
        timeouts = 0
        
        while offset < len(new_raw_buffer) and timeouts < 5:
            try:
                # Try to read data (non-blocking)
                response = self.device.read(1024)
                
                if not response:
                    # No data yet, small sleep and try again
                    time.sleep(0.0001)  # 0.1ms sleep
                    if time.time() - start_read_time > 0.05:  # 50ms timeout
                        timeouts += 1
                    continue
                
                # We got data, process it
                data_len = min(response[4] | (response[5] << 8), 0x3FC) - 8
                if data_len <= 0:
                    continue
                
                # Calculate position in the raw buffer from the response header
                pos = response[8] | (response[9] << 8) | (response[10] << 16) | (response[11] << 24)
                pos = pos // 2  # Convert byte offset to 16-bit word offset
                
                # Extract data directly to raw buffer
                resp_offset = 0xC  # Data starts at offset 12
                
                for j in range(0, data_len, 2):
                    idx = pos + j//2
                    if idx < 160 * 80:
                        new_raw_buffer[idx] = response[resp_offset + j] | (response[resp_offset + j + 1] << 8)
                
                offset += data_len // 2
                            
            except Exception as e:
                print(f"Error reading from device: {e}")
                return
        
        # Direct reshape and put in queue
        try:
            self.frame_queue.put_nowait(new_raw_buffer.reshape(80, 160))
        except queue.Full:
            pass  # Skip this frame if queue is full
    
    def device_loop(self):
        """Main loop for reading from the device."""
        while self.running:
            self.read_frame_buffer_optimized()
    
    def gui_loop(self):
        """Main loop for updating the GUI."""
        if self.running:
            self.update_display()
            # Target 60+ FPS by updating every 16ms
            self.root.after(16, self.gui_loop)
    
    def start(self):
        """Start the listener."""
        if self.find_and_open_device():
            self.running = True
            
            # Start device reader thread with higher priority
            self.reader_thread = threading.Thread(target=self.device_loop, daemon=True)
            self.reader_thread.start()
            
            # Start GUI update loop
            self.gui_loop()
            
            # Run the Tkinter main loop
            self.root.mainloop()
        else:
            print("Failed to start HID listener - device not found or could not be opened")

if __name__ == "__main__":
    # Create and start the HID listener
    listener = HIDListener()
    listener.start()