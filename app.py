from flask import Flask, request, jsonify, send_file
import base64
from PIL import Image
import io

app = Flask(__name__)

def process_image(image_bytes, output_width=800, output_height=1067):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    margin = 0.05
    max_w = int(output_width * (1 - margin * 2))
    max_h = int(output_height * (1 - margin * 2))

    scale = min(max_w / img.width, max_h / img.height)
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)

    img_resized = img.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (output_width, output_height), (255, 255, 255, 255))
    offset_x = (output_width - new_w) // 2
    offset_y = (output_height - new_h) // 2
    canvas.paste(img_resized, (offset_x, offset_y), img_resized)

    canvas_rgb = canvas.convert("RGB")
    output = io.BytesIO()
    canvas_rgb.save(output, format="WEBP", quality=90)
    output.seek(0)
    return output

@app.route("/process", methods=["POST"])
def process():
    # Accept both multipart form and JSON with base64
    if request.content_type and "multipart" in request.content_type:
        if "image" not in request.files:
            return jsonify({"error": "Missing image file"}), 400
        image_bytes = request.files["image"].read()
    else:
        data = request.get_json()
        if not data or "image" not in data or not data["image"]:
            return jsonify({"error": "Missing image data"}), 400
        try:
            image_bytes = base64.b64decode(data["image"])
        except Exception as e:
            return jsonify({"error": f"Base64 decode failed: {str(e)}"}), 400

    try:
        result = process_image(image_bytes)
        return send_file(result, mimetype="image/webp", download_name="output.webp")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
