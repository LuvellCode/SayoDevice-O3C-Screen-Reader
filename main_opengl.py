import hid
import time
import threading
import numpy as np
import queue
import sys
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import glfw

from PIL import Image

# Icon only
import base64
from io import BytesIO

ICON = "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"


HID_DEFAULT_UPDATE_FREQUENCY = 200  # Hardcoded 200, so 1/200 will allow us to display 144 FPS while not pinging the device too often

class HIDListener:
    def __init__(self, fps_limit=60, vendor_id=0x8089, product_id=0x0009, usage_page=0xFF12):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.usage_page = usage_page
        self.device = None
        self.running = False
        self.width, self.height = 160, 80
        self.display_scale = 4
        self.frame_buffer = np.zeros((self.height, self.width), dtype=np.uint16)
        self.raw_buffer = np.zeros(self.width * self.height, dtype=np.uint16)
        self.last_update_time = time.time()
        self.fps_limit = fps_limit if fps_limit>0 else HID_DEFAULT_UPDATE_FREQUENCY
        self.fps_counter = 0
        self.fps = 0
        self.frame_queue = queue.Queue(maxsize=2)  # Buffer for frames between threads
        self.texture_data = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.base_title = "SayoDevice HID Viewer (OpenGL)"
        
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
    
    def setup_opengl(self):
        """Initialize OpenGL context and resources."""
        # Initialize GLFW
        if not glfw.init():
            print("Failed to initialize GLFW")
            return False
        
        # Create a window without resizing
        window_width = self.width * self.display_scale
        window_height = self.height * self.display_scale
        
        # Create GLFW window
        self.window = glfw.create_window(window_width, window_height, self.base_title, None, None)
        if not self.window:
            glfw.terminate()
            print("Failed to create GLFW window")
            return False
        
        # Icon
        glfw.set_window_icon(self.window, 1, Image.open(BytesIO(base64.b64decode(ICON))))

        # Make the window's context current
        glfw.make_context_current(self.window)
        
        # Set callback for window close
        glfw.set_window_close_callback(self.window, self.on_close_callback)
        
        # Setup OpenGL for 2D rendering
        glViewport(0, 0, window_width, window_height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, 1, 0, 1, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Disable depth testing as we're doing 2D
        glDisable(GL_DEPTH_TEST)
        
        # Create texture for frame data
        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        
        # Set texture parameters
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        
        # Initialize texture data
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.width, self.height, 
                     0, GL_RGB, GL_UNSIGNED_BYTE, self.texture_data)
        
        # Create lookup tables for RGB565 to RGB888 conversion
        self.r_lut = np.zeros(32, dtype=np.uint8)
        self.g_lut = np.zeros(64, dtype=np.uint8)
        self.b_lut = np.zeros(32, dtype=np.uint8)
        
        for i in range(32):
            self.r_lut[i] = (i << 3) | (i >> 2)
        for i in range(64):
            self.g_lut[i] = (i << 2) | (i >> 4)
        for i in range(32):
            self.b_lut[i] = (i << 3) | (i >> 2)
            
        # Setup buffers for rendering a full-screen quad
        self.setup_fullscreen_quad()
        
        return True
    
    def setup_fullscreen_quad(self):
        """Setup vertex data for a fullscreen quad."""
        # We'll use simple immediate mode for this example
        # For production, VBOs would be more efficient
        self.vertices = [
            # x, y, s, t
            (0.0, 0.0, 0.0, 0.0),   # Bottom left
            (1.0, 0.0, 1.0, 0.0),   # Bottom right
            (1.0, 1.0, 1.0, 1.0),   # Top right
            (0.0, 1.0, 0.0, 1.0),   # Top left
        ]
    
    def on_close_callback(self, window):
        """Handle window close event."""
        self.running = False
        
    def update_display(self):
        """Update the display with current frame buffer data."""
        try:
            # Try to get a new frame if available
            new_frame = self.frame_queue.get_nowait()
            self.frame_buffer = new_frame
            self.frame_queue.task_done()
            
            # Use vectorized operations for faster processing
            r = self.r_lut[(self.frame_buffer >> 11) & 0x1F]
            g = self.g_lut[(self.frame_buffer >> 5) & 0x3F]
            b = self.b_lut[self.frame_buffer & 0x1F]
            
            # Update texture data
            self.texture_data = np.stack([r, g, b], axis=2)
            
            # Update the texture
            glBindTexture(GL_TEXTURE_2D, self.texture_id)
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, self.width, self.height,
                            GL_RGB, GL_UNSIGNED_BYTE, self.texture_data)
            
        except queue.Empty:
            pass  # Use last frame if no new one is available
        
        # Clear the screen
        glClear(GL_COLOR_BUFFER_BIT)
        
        # Draw a fullscreen quad with our texture
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        
        glBegin(GL_QUADS)
        for x, y, s, t in self.vertices:
            glTexCoord2f(s, 1-t)
            glVertex2f(x, y)
        glEnd()
        
        # Display FPS in the window title
        self.fps_counter += 1
        current_time = time.time()
        if current_time - self.last_update_time >= 1.0:
            self.fps = self.fps_counter
            glfw.set_window_title(self.window, f"{self.base_title} - FPS: {self.fps}")
            self.fps_counter = 0
            self.last_update_time = current_time
        
        # Swap buffers to display the frame
        glfw.swap_buffers(self.window)
        
        # Poll for events
        glfw.poll_events()
    
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
        new_raw_buffer = np.zeros(self.width * self.height, dtype=np.uint16)
        
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
                    if idx < self.width * self.height:
                        new_raw_buffer[idx] = response[resp_offset + j] | (response[resp_offset + j + 1] << 8)
                
                offset += data_len // 2
                            
            except Exception as e:
                print(f"Error reading from device: {e}")
                return
        
        # Direct reshape and put in queue
        try:
            self.frame_queue.put_nowait(new_raw_buffer.reshape(self.height, self.width))
        except queue.Full:
            pass  # Skip this frame if queue is full
    
    def prepare_packets(self):
        """Build optimized packet structures."""
        self.packets = []
        
        chunk_size = 0x3F4  # Original chunk size
        total_size = self.width * self.height * 2
        
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
    
    def device_loop(self):
        """Main loop for reading from the device."""
        while self.running:
            if glfw.window_should_close(self.window):
                self.running = False
                break
            self.read_frame_buffer_optimized()
    
    def start(self):
        """Start the listener."""
        if self.find_and_open_device():
            self.running = True
            
            # Prepare packets once 
            self.prepare_packets()
            
            # Setup OpenGL
            if not self.setup_opengl():
                print("Failed to setup OpenGL")
                return
            
            # Start device reader thread
            self.reader_thread = threading.Thread(target=self.device_loop, daemon=True)
            self.reader_thread.start()
            
            # Main rendering loop
            try:
                while self.running and not glfw.window_should_close(self.window):
                    self.update_display()
                    
                    # FPS control (kinda meh but whatever)
                    # musthave not to overload the PC
                    time.sleep(1/self.fps_limit)
            except Exception as e:
                print(f"Error in main loop: {e}")
            finally:
                # Clean up
                if self.device:
                    self.device.close()
                glfw.terminate()
        else:
            print("Failed to start HID listener - device not found or could not be opened")

if __name__ == "__main__":
    # Create and start the HID listener
    # listener = HIDListener(fps_limit=71)  # 60 +-5 FPS
    listener = HIDListener(fps_limit=0)     # unlim (144) FPS
    listener.start()