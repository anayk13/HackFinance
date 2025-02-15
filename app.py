from flask import Flask, render_template, request, jsonify
import PyPDF2
import os
from transformers import pipeline

app = Flask(__name__)

# Load summarization model
summarizer = pipeline("summarization")

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)

    # Extract text from PDF
    pdf_text = extract_text_from_pdf(file_path)

    print("\nExtracted Text:\n", pdf_text)  # Debugging Step 1 ✅

    if not pdf_text.strip():
        return jsonify({"error": "Could not extract text from PDF"}), 500

    # Summarize text
    summary = generate_summary(pdf_text)

    print("\nGenerated Summary:\n", summary)  # Debugging Step 2 ✅

    return jsonify({"summary": summary})

def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"

    return text

def generate_summary(text):
    if len(text) > 1024:
        chunks = [text[i : i + 1024] for i in range(0, len(text), 1024)]
        summarized_chunks = [summarizer(chunk, max_length=150, min_length=50, do_sample=False)[0]["summary_text"] for chunk in chunks]
        return " ".join(summarized_chunks)

    return summarizer(text, max_length=150, min_length=50, do_sample=False)[0]["summary_text"]

if __name__ == "__main__":
    app.run(debug=True)
