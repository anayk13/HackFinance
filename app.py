from flask import Flask, request, render_template, jsonify
import os
import fitz  # PyMuPDF for PDF text extraction
import docx  # python-docx for DOCX text extraction
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from werkzeug.utils import secure_filename
import re

nltk.download('punkt')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

INSURANCE_KEYWORDS = {
    "coverage", "premium", "policyholder", "exclusions", "deductible", 
    "endorsement", "claim", "policy term", "insurance", "liability"
}

POLICY_SECTIONS = {
    "coverage": ["Coverage", "Insurance Coverage", "What is Covered", "Benefits"],
    "exclusions": ["Exclusions", "What is Not Covered", "Limitations", "Exceptions"],
    "claims": ["Claims", "Claim Process", "How to Claim", "Filing a Claim"],
    "premium": ["Premium", "Payment Details", "Cost", "Premium Schedule"],
    "terms": ["Terms & Conditions", "General Conditions", "Policy Terms"]
}

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
    return len(INSURANCE_KEYWORDS.intersection(words)) >= 3

def find_section_content(text, section_keywords):
    """Find content for a specific section using its keywords."""
    content = []
    lines = text.split("\n")
    in_section = False
    
    for i, line in enumerate(lines):
        # Check if this line starts a section
        if any(keyword.lower() in line.lower() for keyword in section_keywords):
            in_section = True
            continue
        
        # Check if we've reached the next section
        if in_section and i < len(lines) - 1:
            next_line = lines[i + 1]
            if any(any(keyword.lower() in next_line.lower() for keyword in section_list) 
                   for section_list in POLICY_SECTIONS.values()):
                in_section = False
        
        if in_section and line.strip():
            content.append(line.strip())
    
    return " ".join(content)

def extract_policy_sections(text):
    """Extract and organize policy sections with improved structure."""
    sections = {}
    
    for section_key, keywords in POLICY_SECTIONS.items():
        content = find_section_content(text, keywords)
        if content:
            sections[section_key] = content
    
    return sections

def summarize_section(text, num_sentences=5):
    """Generate a detailed summary with bullet points for a section."""
    if not text.strip():
        return []
    
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, num_sentences)
    
    # Convert summary sentences to bullet points
    bullet_points = []
    for sentence in summary:
        # Clean and format the sentence
        point = str(sentence).strip()
        if point and len(point) > 20:  # Ensure meaningful points
            bullet_points.append(point)
    
    return bullet_points

def process_document(text):
    """Process the document and return organized summaries."""
    if not is_insurance_policy(text):
        return None
    
    sections = extract_policy_sections(text)
    summaries = {}
    
    for section_key, content in sections.items():
        summaries[section_key] = summarize_section(content)
    
    return summaries

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
    summaries = process_document(text)

    if not summaries:
        return jsonify({"error": "Uploaded document is not an insurance policy."}), 400

    return render_template('result.html', summaries=summaries)

if __name__ == '__main__':
    app.run(debug=True)