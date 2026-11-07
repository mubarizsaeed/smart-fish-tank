from IPython.display import display, Image, Audio

import cv2  # We're using OpenCV to read video, to install !pip install opencv-python
import base64
import time
from openai import OpenAI
import os
import requests

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])  # export OPENAI_API_KEY first; never hard-code it

video = cv2.VideoCapture("data/fish.mp4")

base64Frames = []
while video.isOpened():
    success, frame = video.read()
    if not success:
        break
    _, buffer = cv2.imencode(".jpg", frame)
    base64Frames.append(base64.b64encode(buffer).decode("utf-8"))

video.release()
print(len(base64Frames), "frames read.")

display_handle = display(Image(data=b""), display_id=True)
for img in base64Frames[0::50]:
    display(Image(data=base64.b64decode(img.encode("utf-8"))))
    time.sleep(0.025)


PROMPT_MESSAGES = [
    {
        "role": "user",
        "content": [
            "These are frames from a video, what decoration are in the tank?",
            *map(lambda x: {"image": x, "resize": 768}, base64Frames[0::50]),
        ],
    },
]

params = {
    "model": "gpt-4o-mini",
    "messages": PROMPT_MESSAGES,
    "max_tokens": 200,
}

# Get response
result = client.chat.completions.create(**params)
print(result.choices[0].message.content)
