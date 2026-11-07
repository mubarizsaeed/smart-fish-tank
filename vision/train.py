from ultralytics import YOLO

# Load a pretrained YOLOv8n model
model = YOLO('yolov8n.pt')

# Train the model
model.train(
    data='config/dataset.yaml',  # run from the vision/ folder
    epochs=200,  # Number of epochs
    imgsz=960,   # Image size
    batch=8,     # Batch size
    name='fish_model', # Name for this training run
    device='cpu' 
)