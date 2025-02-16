from flask import Flask, request, render_template, jsonify, session
import os
import fitz  # PyMuPDF
import docx
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from werkzeug.utils import secure_filename
import re
from datetime import datetime

nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for session
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Constants and configurations
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

COMMON_REJECTION_REASONS = {
    "pre_existing": ["pre-existing condition", "prior condition", "existing condition"],
    "coverage_limit": ["coverage limit", "maximum benefit", "limit exceeded"],
    "policy_exclusion": ["excluded", "not covered", "exclusion applies"],
    "documentation": ["insufficient documentation", "missing documentation"],
    "timeline": ["time limit", "filing deadline", "late submission"]
}

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join([page.get_text("text") for page in doc])

def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text(file_path):
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
    words = set(text.lower().split())
    return len(INSURANCE_KEYWORDS.intersection(words)) >= 3

def find_section_content(text, section_keywords):
    content = []
    lines = text.split("\n")
    in_section = False
    
    for i, line in enumerate(lines):
        if any(keyword.lower() in line.lower() for keyword in section_keywords):
            in_section = True
            continue
        
        if in_section and i < len(lines) - 1:
            next_line = lines[i + 1]
            if any(any(keyword.lower() in next_line.lower() for keyword in section_list) 
                   for section_list in POLICY_SECTIONS.values()):
                in_section = False
        
        if in_section and line.strip():
            content.append(line.strip())
    
    return " ".join(content)

def extract_policy_sections(text):
    sections = {}
    for section_key, keywords in POLICY_SECTIONS.items():
        content = find_section_content(text, keywords)
        if content:
            sections[section_key] = content
    return sections

def summarize_section(text, num_sentences=5):
    if not text.strip():
        return []
    
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, num_sentences)
    
    bullet_points = []
    for sentence in summary:
        point = str(sentence).strip()
        if point and len(point) > 20:
            bullet_points.append(point)
    
    return bullet_points

def process_document(text):
    if not is_insurance_policy(text):
        return None
    
    sections = extract_policy_sections(text)
    summaries = {}
    
    for section_key, content in sections.items():
        summaries[section_key] = summarize_section(content)
    
    return summaries

def analyze_claim_rejection(policy_text, rejection_reason, claim_details):
    policy_text_lower = policy_text.lower()
    rejection_reason_lower = rejection_reason.lower()
    
    analysis = {
        "valid_rejection": True,
        "discrepancies": [],
        "policy_references": [],
        "appeal_points": [],
        "recommend_appeal": False
    }
    
    # Extract relevant sections
    relevant_sections = []
    for section in POLICY_SECTIONS["exclusions"] + POLICY_SECTIONS["coverage"]:
        section_lower = section.lower()
        if section_lower in policy_text_lower:
            start_idx = policy_text_lower.find(section_lower)
            end_idx = policy_text_lower.find("\n\n", start_idx)
            if end_idx == -1:
                end_idx = len(policy_text_lower)
            relevant_sections.append(policy_text[start_idx:end_idx])

    # Analyze discrepancies
    for section in relevant_sections:
        section_lower = section.lower()
        
        # Check explicit exclusions
        if any(reason in section_lower for reason in COMMON_REJECTION_REASONS["policy_exclusion"]):
            if not any(term in section_lower for term in rejection_reason_lower.split()):
                analysis["discrepancies"].append(f"Rejection reason not explicitly listed in policy exclusions")
                analysis["policy_references"].append(section.strip())
                analysis["recommend_appeal"] = True

        # Check coverage exceptions
        if "coverage" in section_lower and rejection_reason_lower in section_lower:
            if "except" in section_lower or "unless" in section_lower:
                analysis["discrepancies"].append("Possible exception to exclusion found")
                analysis["policy_references"].append(section.strip())
                analysis["recommend_appeal"] = True

        # Check timeline requirements
        if any(term in rejection_reason_lower for term in COMMON_REJECTION_REASONS["timeline"]):
            if "days" in section_lower or "within" in section_lower:
                analysis["discrepancies"].append("Timeline requirements may have exceptions")
                analysis["policy_references"].append(section.strip())

    if analysis["recommend_appeal"]:
        analysis["appeal_points"] = generate_appeal_points(
            rejection_reason,
            claim_details,
            analysis["discrepancies"],
            analysis["policy_references"]
        )
        analysis["valid_rejection"] = False

    return analysis

def generate_appeal_points(rejection_reason, claim_details, discrepancies, policy_references):
    appeal_points = []
    
    # Introduction
    appeal_points.append({
        "type": "introduction",
        "content": f"I am writing to appeal the rejection of my insurance claim based on {rejection_reason}."
    })
    
    # Policy references
    for ref in policy_references:
        appeal_points.append({
            "type": "policy_reference",
            "content": f"According to the policy section stating '{ref}', my claim should be eligible for coverage."
        })
    
    # Discrepancies
    for disc in discrepancies:
        appeal_points.append({
            "type": "discrepancy",
            "content": f"There appears to be a discrepancy in the rejection: {disc}"
        })
    
    # Claim details
    appeal_points.append({
        "type": "claim_details",
        "content": f"The details of my claim ({claim_details}) clearly fall within the policy's coverage terms."
    })
    
    # Conclusion
    appeal_points.append({
        "type": "conclusion",
        "content": "Based on these points, I respectfully request a review and reconsideration of my claim."
    })
    
    return appeal_points

def generate_appeal_letter(appeal_points, policyholder_name):
    current_date = datetime.now().strftime("%B %d, %Y")
    
    letter = f"""
{current_date}

Insurance Claims Department
[Insurance Company Name]
[Address]

RE: Appeal for Claim Rejection

Dear Claims Review Department,

{appeal_points[0]['content']}

"""
    
    # Add policy references and discrepancies
    for point in appeal_points[1:-1]:
        letter += f"\n{point['content']}\n"
    
    # Add conclusion
    letter += f"""
{appeal_points[-1]['content']}

Thank you for your time and consideration of this appeal.

Sincerely,
{policyholder_name}
"""
    
    return letter

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

    session['policy_text'] = text
    return render_template('result.html', summaries=summaries)

@app.route('/analyze_claim', methods=['POST'])
def analyze_claim():
    data = request.json
    policy_text = session.get('policy_text', '')
    
    if not policy_text:
        return jsonify({"error": "Please upload policy document first"}), 400
        
    analysis = analyze_claim_rejection(
        policy_text,
        data['rejection_reason'],
        data['claim_details']
    )
    
    if analysis['recommend_appeal']:
        appeal_letter = generate_appeal_letter(
            analysis['appeal_points'],
            data['policyholder_name']
        )
        analysis['appeal_letter'] = appeal_letter
    
    return jsonify(analysis)

if __name__ == '__main__':
    app.run(debug=True)
