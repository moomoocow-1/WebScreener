import json
from flask import Flask, Response, request, jsonify
from PIL import Image
import threading
import time

AUTH_FILE = "auth.json"
app = Flask(__name__)

# ---- Load / save auth ----
def load_auth():
    with open(AUTH_FILE, "r") as f:
        return json.load(f)

def save_auth(data):
    with open(AUTH_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_client_ip():
    # Cloudflare headers or normal
    if "CF-Connecting-IP" in request.headers:
        return request.headers["CF-Connecting-IP"]
    return request.remote_addr

def is_verified(ip):
    auth = load_auth()
    return ip in auth["verified_ips"]

# ---- Product key endpoint ----
@app.route("/verify", methods=["POST"])
def verify_key():
    data = request.json
    if not data or "key" not in data:
        return jsonify({"error": "Missing key"}), 400

    key = data["key"]
    ip = get_client_ip()
    auth = load_auth()

    if ip in auth["verified_ips"]:
        return jsonify({"status": "already_verified"})

    if key not in auth["valid_keys"]:
        return jsonify({"error": "Invalid or used key"}), 403

    # Mark key as used
    auth["valid_keys"].remove(key)
    auth["used_keys"][key] = ip
    auth["verified_ips"].append(ip)
    save_auth(auth)

    return jsonify({"status": "verified"})

# ---- MJPEG streaming ----
latest_frame = None
frame_lock = threading.Lock()

@app.route("/frame", methods=["POST"])
def receive_frame():
    global latest_frame
    with frame_lock:
        latest_frame = request.data
    return "ok"

@app.route("/video")
def video():
    ip = get_client_ip()
    if not is_verified(ip):
        return "Unauthorized. Verify your key at /verify.", 403

    def generate():
        while True:
            with frame_lock:
                frame = latest_frame
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            time.sleep(0.05)

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

# ---- Root test ----
@app.route("/")
def index():
    return "Server is live! Verify first at /verify."

if __name__ == "__main__":
    import os
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
