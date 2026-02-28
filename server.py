from flask import Flask, Response, request
from PIL import Image
import threading
import time

app = Flask(__name__)

# Global frame buffer
latest_frame = None
frame_lock = threading.Lock()

@app.route("/")
def index():
    return "Server is running! Go to /video for the stream."

# Endpoint for PC agent to POST JPEG frames
@app.route("/frame", methods=["POST"])
def receive_frame():
    global latest_frame
    with frame_lock:
        latest_frame = request.data
    return "ok"

# MJPEG stream for Chromebook
@app.route("/video")
def video():
    def generate():
        while True:
            with frame_lock:
                frame = latest_frame
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" +
                    frame +
                    b"\r\n"
                )
            time.sleep(0.05)  # ~20 FPS

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    import os
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
