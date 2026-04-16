from flask import Flask, request, jsonify, send_file
import base64
from PIL import Image
import io

app = Flask(__name__)

def decode_image_data(raw_data):
    """Try multiple approaches to get valid image bytes."""
    candidates = []

    if isinstance(raw_data, bytes):
        candidates.append(raw_data)
        # Maybe it's base64 as ASCII bytes
        try:
            as_string = raw_data.decode("ascii").strip()
            candidates.append(base64.b64decode(as_string))
        except:
            pass
        # Try direct base64 decode of bytes
        try:
            candidates.append(base64.b64decode(raw_data.strip()))
        except:
            pass

    elif isinstance(raw_data, str):
        try:
            candidates.append(base64.b64decode(raw_data.strip()))
        except:
            pass
        candidates.append(raw_data.encode("latin-1"))

    for candidate in candidates:
        try:
            buf = io.BytesIO(candidate)
            img = Image.open(buf)
            img.verify()
            return candidate
        except:
            continue

    raise ValueError(f"Cannot decode. Tried {len(candidates)} methods. First 20 bytes: {raw_data[:20] if raw_data else 'empty'}")

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
    raw_data = None

    if request.content_type and "multipart" in request.content_type:
        if "image" not in request.files:
            return jsonify({"error": "Missing image file"}), 400
        raw_data = request.files["image"].read()
    else:
        data = request.get_json()
        if not data or "image" not in data or not data["image"]:
            return jsonify({"error": "Missing image data"}), 400
        raw_data = data["image"]

    try:
        image_bytes = decode_image_data(raw_data)
        result = process_image(image_bytes)
        return send_file(result, mimetype="image/webp", download_name="output.webp")
    except Exception as e:
        first_bytes = raw_data[:40] if isinstance(raw_data, bytes) else str(raw_data)[:40]
        return jsonify({
            "error": str(e),
            "data_type": str(type(raw_data)),
            "data_length": len(raw_data) if raw_data else 0,
            "first_bytes": str(first_bytes)
        }), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
