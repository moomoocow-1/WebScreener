import json
from flask import Flask, request, jsonify, render_template
from flask_sock import Sock
import os

app = Flask(__name__)
sock = Sock(app)
AUTH_FILE = "auth.json"

# ---- Auth helper functions ----
def load_auth():
    with open(AUTH_FILE, "r") as f:
        return json.load(f)

def save_auth(data):
    with open(AUTH_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_client_ip():
    if "CF-Connecting-IP" in request.headers:
        return request.headers["CF-Connecting-IP"]
    return request.remote_addr

def is_verified(ip):
    auth = load_auth()
    return ip in auth["verified_ips"]

# ---- Product key verification ----
@app.route("/verify", methods=["GET", "POST"])
def verify_key():
    if request.method == "GET":
        return '''
            <h2>Enter Product Key</h2>
            <form method="POST">
                Product Key: <input name="key" required>
                <input type="submit" value="Verify">
            </form>
        '''
    key = request.form.get("key")
    ip = get_client_ip()
    auth = load_auth()
    if ip in auth["verified_ips"]:
        return "<h3>Already verified!</h3><a href='/'>Go to Control</a>"
    if key not in auth["valid_keys"]:
        return "<h3>Invalid or used key!</h3>"
    auth["valid_keys"].remove(key)
    auth["used_keys"][key] = ip
    auth["verified_ips"].append(ip)
    save_auth(auth)
    return "<h3>Verified!</h3><a href='/'>Go to Control</a>"

# ---- Landing page ----
@app.route("/")
def index():
    return '''
        <h1>Remote Desktop Control</h1>
        <p>Verified? Open <a href="/control.html">Control Panel</a></p>
    '''

# ---- WebRTC signaling route ----
@app.route("/offer", methods=["POST"])
def offer():
    ip = get_client_ip()
    if not is_verified(ip):
        return "Unauthorized", 403

    data = request.json
    # save offer for PC agent to answer
    with open("offer.json", "w") as f:
        json.dump(data, f)
    return jsonify({"status":"ok"})

@app.route("/answer", methods=["GET"])
def answer():
    # PC agent puts answer here
    try:
        with open("answer.json", "r") as f:
            return jsonify(json.load(f))
    except:
        return jsonify({"status":"pending"})

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
