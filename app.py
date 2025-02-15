from flask import Flask, request, render_template, jsonify
import os
import fitz  # PyMuPDF for PDF text extraction
import docx  # python-docx for DOCX text extraction
import nltk
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

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    doc = fitz.open(pdf_path)
    return "\n".join([page.get_text("text") for page in doc])

def extract_text_from_docx(docx_path):
    """Extract text from a DOCX file."""
    doc = docx.Document(docx_path)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text(file_path):
    """Extract text from different file formats."""
    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        return extract_text_from_docx(file_path)
    else:
        with open(file_path, 'rb') as f:
            try:
                return f.read().decode('utf-8')
            except UnicodeDecodeError:
                return f.read().decode('ISO-8859-1')

def is_insurance_policy(text):
    """Check if the document contains insurance-related keywords."""
    words = set(text.lower().split())
    return any(keyword in words for keyword in INSURANCE_KEYWORDS)

def extract_policy_sections(text):
    """Extract relevant sections from the insurance policy text."""
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

def summarize_text(text):
    """Summarize extracted policy sections."""
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, 3)
    return " ".join(str(sentence) for sentence in summary)

@app.route('/')
def index():
    return render_template('index.html')

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

    text = extract_text(filepath)

    if not is_insurance_policy(text):
        return jsonify({"error": "Uploaded document is not an insurance policy."}), 400

    extracted_sections = extract_policy_sections(text)
    summarized_sections = {section: summarize_text(content) for section, content in extracted_sections.items()}

    return render_template('result.html', summary=summarized_sections)

if __name__ == '__main__':
    app.run(debug=True)
