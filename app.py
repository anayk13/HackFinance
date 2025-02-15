from flask import Flask, request, jsonify, render_template
import json
from datetime import datetime
import spacy
from typing import Dict, Optional

app = Flask(__name__)

# Sample policy text - in production, this would come from a database
SAMPLE_POLICY = """
HEALTH INSURANCE POLICY
Policy Number: HIP-2024-12345
Issue Date: 02/15/2024

Coverage Start: 02/20/2024
Coverage End: 02/20/2025

Exclusions:
- Pre-existing conditions for the first 12 months
- Cosmetic surgeries
- Alternative therapies

Inclusions:
- Hospitalization coverage
- Prescription drugs
- Emergency services

Claim Retrieval Process:
1. Submit claim within 30 days of treatment
2. Provide original medical bills and reports
3. Wait for processing within 15 business days
"""

class InsuranceClaimBot:
    def __init__(self):
        self.policy_text = SAMPLE_POLICY
        self.conversation_history = []
        self.current_policy = None
        
    def analyze_claim(self, rejection_reason: str) -> Dict:
        """Analyze claim rejection against policy terms"""
        rejection_lower = rejection_reason.lower()
        
        # Analysis logic based on rejection reason
        if "pre-authorization" in rejection_lower:
            return {
                "status": "conditional",
                "reason": "Pre-authorization requirement",
                "policy_reference": "Pre-authorization required for non-emergency services",
                "recommendation": "Check if service was emergency or if pre-auth was obtained",
                "next_steps": [
                    "Gather emergency documentation if applicable",
                    "Check pre-authorization records",
                    "File appeal within 30 days"
                ]
            }
            
        elif "medical necessity" in rejection_lower:
            return {
                "status": "appealable",
                "reason": "Medical necessity questioned",
                "policy_reference": "Services must be medically necessary",
                "recommendation": "Gather documentation supporting medical necessity",
                "next_steps": [
                    "Get physician statement",
                    "Collect medical records",
                    "Submit appeal with documentation"
                ]
            }
            
        elif "out of network" in rejection_lower:
            return {
                "status": "appealable",
                "reason": "Out-of-network provider",
                "policy_reference": "Out-of-network services require prior approval",
                "recommendation": "Check if emergency or no in-network providers available",
                "next_steps": [
                    "Document network provider search",
                    "Get emergency documentation if applicable",
                    "Request gap exception"
                ]
            }
            
        else:
            return {
                "status": "contestable",
                "reason": "Non-standard rejection",
                "policy_reference": "No matching exclusion found",
                "recommendation": "Appeal based on policy coverage",
                "next_steps": [
                    "Request detailed explanation",
                    "Review policy terms",
                    "File appeal"
                ]
            }

    def generate_appeal_letter(self, analysis: Dict) -> str:
        """Generate appeal letter template based on analysis"""
        template = f"""Dear Claims Department,

        I am writing to appeal the denial of my insurance claim. The claim was denied due to {analysis['reason']}.

        {analysis['recommendation']}

        Please review this appeal and the attached documentation:
        {chr(10).join('- ' + step for step in analysis['next_steps'])}

        Thank you for your consideration.

        Sincerely,
        [Name]
        [Policy Number]
        """
        return template

    def summarize_policy(self, option: str) -> str:
        """Summarize specific sections of the policy based on user selection"""
        summaries = {
            "Policy Timelines": "Coverage Start: 02/20/2024, Coverage End: 02/20/2025",
            "Policy Exclusions": "- Pre-existing conditions for the first 12 months\n- Cosmetic surgeries\n- Alternative therapies",
            "Policy Inclusions": "- Hospitalization coverage\n- Prescription drugs\n- Emergency services",
            "Claim Retrievals": "1. Submit claim within 30 days of treatment\n2. Provide original medical bills and reports\n3. Wait for processing within 15 business days",
            "General Summary": "This health insurance policy provides coverage for hospitalization, prescription drugs, and emergency services, but excludes pre-existing conditions (first 12 months), cosmetic surgeries, and alternative therapies. Claims must be submitted within 30 days of treatment."
        }
        return summaries.get(option, "Invalid selection. Please choose a valid option.")

# Flask routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_claim():
    data = request.json
    rejection_reason = data.get('rejection_reason', '')
    
    bot = InsuranceClaimBot()
    analysis = bot.analyze_claim(rejection_reason)
    appeal_letter = bot.generate_appeal_letter(analysis)
    
    return jsonify({
        'analysis': analysis,
        'appeal_letter': appeal_letter
    })

@app.route('/api/summarize', methods=['POST'])
def summarize_policy():
    data = request.json
    option = data.get('option', '')
    
    bot = InsuranceClaimBot()
    summary = bot.summarize_policy(option)
    
    return jsonify({
        'summary': summary
    })

@app.route('/api/upload_policy', methods=['POST'])
def upload_policy():
    # In production, handle actual file upload
    return jsonify({
        'status': 'success',
        'message': 'Policy processed successfully'
    })

if __name__ == '__main__':
    app.run(debug=True)
    