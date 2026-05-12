import os
import json
import base64
import anthropic
import fitz  # PyMuPDF
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path

app = Flask(__name__)
CORS(app)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

PDF_PATH = "report.pdf"
pdf_content = []
persona_system = ""

PERSONA = {
    "name": "Karen",
    "age": 44,
    "city": "Mississauga",
    "description": "Gen X female, family with kids, Loblaws shopper, household income $100K-$150K",
    "initials": "KA"
}

def load_pdf():
    global pdf_content
    if not Path(PDF_PATH).exists():
        print("No PDF found at report.pdf")
        return
    print("Loading PDF...")
    doc = fitz.open(PDF_PATH)
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img_bytes = pix.tobytes("png")
        img_b64 = base64.standard_b64encode(img_bytes).decode("utf-8")
        pdf_content.append({
            "page": page_num + 1,
            "text": text,
            "image_b64": img_b64
        })
    print(f"PDF loaded: {len(pdf_content)} pages")

def build_system_prompt():
    return f"""You are {PERSONA['name']}, a {PERSONA['age']}-year-old Canadian woman living in {PERSONA['city']}, Ontario. You are a {PERSONA['description']}. You love mushrooms and buy them regularly at your local Loblaws.

You speak entirely in first person, from personal experience. You are warm, conversational, and genuine. You never sound like a researcher or analyst.

You have access to two sources of information:

1. A research report about Canadian mushroom consumers that has been loaded into your memory. When answering questions about research findings, consumer data, penetration rates, sentiment, or survey results, draw from this report and say something natural like "From the research I have seen on this..." or "I have heard that studies show..."

2. Real time internet search results that will be provided to you when the user asks about current trends, news, or market information. When using this source say something natural like "I just looked this up and from what I am seeing online..." 

Rules:
- Always stay in character as {PERSONA['name']}
- Never break character or refer to yourself as an AI
- Keep answers under 150 words unless asked for more detail
- Be warm, personal and conversational
- If asked your full story or for a detailed answer, you can go longer
- When you do not know something, say so naturally as {PERSONA['name']} would"""

@app.route("/")
def index():
    return send_from_directory(".", "widget.html")

@app.route("/api/persona", methods=["GET"])
def get_persona():
    return jsonify(PERSONA)

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")
    history = data.get("history", [])
    use_search = data.get("use_search", False)

    messages = []

    # Add PDF context for report questions
    if pdf_content and not use_search:
        pdf_context_parts = []
        for page in pdf_content[:8]:  # First 8 pages for context
            if page["text"].strip():
                pdf_context_parts.append({
                    "type": "text",
                    "text": f"[Report Page {page['page']}]: {page['text'][:800]}"
                })
        if pdf_context_parts:
            pdf_context_parts.append({
                "type": "text",
                "text": f"\nUser question: {user_message}"
            })
            messages.append({"role": "user", "content": pdf_context_parts})
            messages.append({"role": "assistant", "content": "I have reviewed the research report. I will answer based on what I have seen in it."})

    # Add conversation history
    for msg in history[-6:]:  # Last 6 messages for context
        messages.append(msg)

    # Add current message
    if use_search:
        messages.append({
            "role": "user",
            "content": f"The user wants current information. Please answer this question using your web search tool, then respond in character as {PERSONA['name']}: {user_message}"
        })
    else:
        messages.append({"role": "user", "content": user_message})

    try:
        if use_search:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=600,
                system=build_system_prompt(),
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=messages
            )
        else:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=600,
                system=build_system_prompt(),
                messages=messages
            )

        reply = ""
        for block in response.content:
            if block.type == "text":
                reply += block.text

        return jsonify({"reply": reply, "persona": PERSONA})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/upload-pdf", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename.endswith(".pdf"):
        return jsonify({"error": "File must be a PDF"}), 400
    file.save(PDF_PATH)
    load_pdf()
    return jsonify({"success": True, "pages": len(pdf_content)})

# Load PDF on startup
load_pdf()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
