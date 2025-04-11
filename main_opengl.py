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