from flask import Flask, Response, render_template
import cv2
import threading
import time
from collections import deque
import logging
import os
from waitress.channel import ClientDisconnected

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='stream_server.log'
)

class CameraManager:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.camera = None
        self.lock = threading.Lock()
        self.last_frame = None
        self.is_running = True
        self.reconnect_delay = 10  # seconds
        self.init_camera()

    def init_camera(self):
        """Initialize the camera with settings"""
        with self.lock:
            if self.camera is not None:
                self.camera.release()

            # Wait for the device to be available
            while self.is_running and not os.path.exists(f"/dev/video{self.camera_index}"):
                logging.warning(f"Waiting for camera device: /dev/video{self.camera_index}")
                time.sleep(self.reconnect_delay)

            self.camera = cv2.VideoCapture(self.camera_index)

            if not self.camera.isOpened():
                logging.error("Failed to open camera")
                return False

            # Configure camera settings
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize frame buffer

            # Verify settings were applied
            actual_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.camera.get(cv2.CAP_PROP_FPS)

            logging.info(f"Camera initialized - Resolution: {actual_width}x{actual_height}, FPS: {actual_fps}")
            return True

    def read_frame(self):
        """Read a frame from the camera with error handling"""
        with self.lock:
            if self.camera is None or not self.camera.isOpened():
                return False, None

            try:
                ret, frame = self.camera.read()
                if not ret:
                    logging.warning("Failed to read frame, attempting to reinitialize camera")
                    self.init_camera()
                    return False, None
                return True, frame
            except Exception as e:
                logging.error(f"Error reading frame: {str(e)}")
                return False, None

    def release(self):
        """Release the camera resources"""
        self.is_running = False
        with self.lock:
            if self.camera is not None:
                self.camera.release()
                self.camera = None

app = Flask(__name__)
camera_manager = CameraManager(0)  # or whatever your camera index is
frame_buffer = deque(maxlen=2)
frame_lock = threading.Lock()
active_connections = 0
connections_lock = threading.Lock()

def capture_frames():
    while camera_manager.is_running:
        try:
            success, frame = camera_manager.read_frame()
            if success:
                with connections_lock:
                    # Adjust quality based on number of connections
                    quality = max(65, 85 - (active_connections * 5))

                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
                ret, buffer = cv2.imencode('.jpg', frame, encode_param)

                if ret:
                    with frame_lock:
                        frame_buffer.append(buffer.tobytes())

            # Adaptive sleep based on FPS target (30 FPS = ~33ms per frame)
            time.sleep(0.033)

        except Exception as e:
            logging.error(f"Error in capture_frames: {str(e)}")
            time.sleep(0.1)

def generate():
    global active_connections

    with connections_lock:
        active_connections += 1
        current_connection = active_connections

    logging.info(f"New connection established. Active connections: {active_connections}")

    try:
        while True:
            try:
                with frame_lock:
                    if frame_buffer:
                        frame_data = frame_buffer[-1]
                        yield (b'--frame\r\n'
                              b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')

                # Adaptive sleep based on connection count
                sleep_time = max(0.033, 0.033 + (current_connection * 0.005))
                time.sleep(sleep_time)

            except ClientDisconnected:
                logging.info("Client disconnected normally")
                break
            except Exception as e:
                logging.error(f"Error in generate: {str(e)}")
                break

    finally:
        with connections_lock:
            active_connections -= 1
            logging.info(f"Connection closed. Remaining connections: {active_connections}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    if active_connections >= 5:
        logging.warning("Connection rejected - too many active connections")
        return "Too many viewers, please try again later!", 503

    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

def cleanup():
    camera_manager.release()
    logging.info("Camera released during shutdown")

import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    # Start capture thread
    capture_thread = threading.Thread(target=capture_frames, daemon=True)
    capture_thread.start()

    # Configure Waitress with error handling
    from waitress import serve

    logging.info("Starting server...")

    try:
        serve(app, host='0.0.0.0', port=5000, threads=5,
              connection_limit=10,
              cleanup_interval=1,
              channel_timeout=30)
    except Exception as e:
        logging.error(f"Server error: {str(e)}")
        cleanup()
