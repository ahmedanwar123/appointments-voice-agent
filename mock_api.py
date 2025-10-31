from flask import Flask, request, jsonify
from uuid import uuid4

app = Flask(__name__)


@app.route("/appointments", methods=["POST"])
def create_appointment():
    data = request.json or {}
    return jsonify({"id": uuid4().hex, "received": data}), 201


# Add this new route
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(port=5000)
