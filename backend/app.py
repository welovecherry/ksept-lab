from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Enable CORS so the frontend can call the API directly (in addition to the
# Vite dev-server proxy). This keeps the API reachable from other origins too.
CORS(app)


@app.route("/api/hello", methods=["GET"])
def hello():
    return jsonify({"message": "Hello from Flask"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
