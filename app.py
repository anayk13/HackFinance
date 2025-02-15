from flask import Flask, request, jsonify, render_template
import os
import nltk
import fitz  # PyMuPDF for PDF extraction
import docx  # python-docx for DOCX extraction
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from werkzeug.utils import secure_filename

nltk.download('punkt')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

INSURANCE_KEYWORDS = {"coverage", "premium", "policyholder", "exclusions", "deductible", "endorsement", "claim", "policy term"}
POLICY_SECTIONS = ["Coverage", "Exclusions", "Claim Process", "Premium Details", "Terms & Conditions"]

# Extract text from PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join([page.get_text("text") for page in doc])

# Extract text from DOCX
def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    return "\n".join([para.text for para in doc.paragraphs])

# Check if text contains insurance-related content
def is_insurance_policy(text):
    words = set(text.lower().split())
    return any(keyword in words for keyword in INSURANCE_KEYWORDS)

# Extract policy sections
def extract_policy_sections(text):
    extracted_sections = {}
    lines = text.split("\n")
    current_section = None
    
    for line in lines:
        line = line.strip()
        if any(section.lower() in line.lower() for section in POLICY_SECTIONS):
            current_section = line
            extracted_sections[current_section] = []
        elif current_section:
            extracted_sections[current_section].append(line)
    
    return {k: " ".join(v) for k, v in extracted_sections.items()}

# Summarize policy sections
def summarize_text(text):
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, 3)
    return " ".join(str(sentence) for sentence in summary)

@app.route('/')
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        if file.filename.endswith('.pdf'):
            text = extract_text_from_pdf(filepath)
        elif file.filename.endswith('.docx'):
            text = extract_text_from_docx(filepath)
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
    except Exception as e:
        return jsonify({"error": "Uploaded file is not a valid text document or contains unsupported encoding."}), 400

    if not is_insurance_policy(text):
        return jsonify({"error": "Uploaded document is not an insurance policy."}), 400

    extracted_sections = extract_policy_sections(text)
    structured_summary = {section: summarize_text(content) for section, content in extracted_sections.items()}
    
    response = {"Structured Policy Summary": structured_summary}
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
