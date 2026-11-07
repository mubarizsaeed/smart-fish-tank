from flask import Flask, Response, render_template, jsonify
import cv2
import threading
import time
import logging
import os
from waitress import serve
import base64
from openai import OpenAI
import markdown2
from ultralytics import YOLO

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class EnhancedCameraManager:
    def __init__(self):
        self.camera = None
        self.camera_index = None
        self.lock = threading.Lock()
        self.is_running = True
        self.model = YOLO(os.environ.get("FISH_MODEL", "Fish_Model_Smaller.pt"))  # weights are git-ignored; train with train.py
        self.model.to('cpu')
        self.colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255),
            (128, 0, 128), (128, 128, 0), (128, 0, 0)
        ]
        self.find_and_init_camera()

    def find_working_camera(self):
        logging.info("Searching for camera...")
        for idx in range(3):
            try:
                logging.info(f"Trying camera index {idx}")
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        logging.info(f"Found working camera at index {idx}")
                        cap.release()
                        return idx
                cap.release()
            except Exception as e:
                logging.warning(f"Error testing camera {idx}: {e}")
            time.sleep(0.5)
        return None

    def find_and_init_camera(self):
        self.camera_index = self.find_working_camera()
        if self.camera_index is not None:
            return self.init_camera()
        raise RuntimeError("No working camera found")

    def init_camera(self):
        logging.info(f"Initializing camera {self.camera_index}")
        if self.camera is not None:
            self.camera.release()
            time.sleep(0.5)
            
        self.camera = cv2.VideoCapture(self.camera_index)
        if not self.camera.isOpened():
            return False
       
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.camera.set(cv2.CAP_PROP_FPS, 30)     
        
        
        
        width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(self.camera.get(cv2.CAP_PROP_FPS))
        logging.info(f"Camera initialized: {width}x{height} @ {fps}fps")

        
        return True

    def process_frame_with_yolo(self, frame):
        results = self.model.predict(
            frame, 
            conf=0.4,       # Lower confidence threshold (was 0.5)
            iou=0.5,        # Lower IoU threshold for more overlapping boxes
            max_det=10,     # Increase max detections
            verbose=False
        )
    
    # Debug print to see what's being detected
        print("Detected objects:", [result.names[int(box.cls[0])] for result in results for box in result.boxes])
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                color = self.colors[class_id % len(self.colors)]
                
                cv2.rectangle(frame, 
                            (int(x1), int(y1)), 
                            (int(x2), int(y2)),
                            color, 2)
                cv2.putText(frame, 
                           class_name,
                           (int(x1), int(y1) - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, color, 2)
        return frame
        

    def get_frame(self):
        with self.lock:
            if not self.camera or not self.camera.isOpened():
                self.find_and_init_camera()
                return None
                
            success, frame = self.camera.read()
            if not success:
                return None
                
            # Process frame with YOLO
            processed_frame = self.process_frame_with_yolo(frame)
                
            ret, jpeg = cv2.imencode('.jpg', processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                return None
            return jpeg.tobytes()

    def get_frame_for_analysis(self):
        with self.lock:
            if not self.camera or not self.camera.isOpened():
                return None
                
            success, frame = self.camera.read()
            if not success:
                return None
                
            # Process frame with YOLO before analysis
            processed_frame = self.process_frame_with_yolo(frame)
                
            ret, buffer = cv2.imencode('.jpg', processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            if not ret:
                return None
            return base64.b64encode(buffer).decode('utf-8')

    def release(self):
        self.is_running = False
        if self.camera:
            self.camera.release()

'''_____________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________'''
app = Flask(__name__)

def generate_frames():
    while camera_manager.is_running:
        frame = camera_manager.get_frame()
        if frame is not None:
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(1/60)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

def convert_markdown_to_html(text):
    return markdown2.markdown(text)

@app.route('/analyze-tank')

def analyze_tank():
    try:
        base64Frames = []
        for _ in range(3):  # Capture 3 frames
            frame_data = camera_manager.get_frame_for_analysis()
            if frame_data:
                base64Frames.append(frame_data)
            time.sleep(0.1)  # Small delay between captures

        if not base64Frames:
            return jsonify({"error": "Failed to capture frames"}), 500

        PROMPT_MESSAGES = [
            {
                "role": "user",
                "content": [
                    """There are 3 cherry barb fish in this tank.
                    Fish 1 is a male and is more orange then the other 2. His name is Gateway.
                    Fish 2 is a female and is more black then the other female. Her name is Phish II.
                    Fish 3 is also a female is is lighter then the other female. Her name is Troy.

                    Please give a description of what each fish is doing if they are visible.
                    Format your response using Markdown for emphasis.
                    """,
                    *map(lambda x: {"image": x, "resize": 768}, base64Frames),
                ],
            },
        ]

        params = {
            "model": "gpt-4o-mini",
            "messages": PROMPT_MESSAGES,
            "max_tokens": 200,
        }

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])  # never hard-code this
        result = client.chat.completions.create(**params)
        
        # Convert markdown to HTML before sending
        html_content = convert_markdown_to_html(result.choices[0].message.content)
        return jsonify({"description": html_content})

    except Exception as e:
        logging.error(f"Analysis error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    try: 
        camera_manager = EnhancedCameraManager()
        logging.info("Starting server...")
        serve(app, host='0.0.0.0', port=5000, threads=8)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        if 'camera_manager' in locals():
            camera_manager.release()
