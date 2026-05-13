import os
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
pdf_pages = []
 
PERSONA = {
    "name": "David",
    "age": 48,
    "city": "Toronto",
    "description": "Consumer Insights Expert, Canadian Produce Industry",
    "initials": "DC"
}
 
def load_pdf():
    global pdf_pages
    if not Path(PDF_PATH).exists():
        print("No PDF found at report.pdf")
        return
    print("Loading PDF...")
    doc = fitz.open(PDF_PATH)
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        img_bytes = pix.tobytes("png")
        img_b64 = base64.standard_b64encode(img_bytes).decode("utf-8")
        pdf_pages.append({
            "page": page_num + 1,
            "text": text,
            "image_b64": img_b64
        })
    print(f"PDF loaded: {len(pdf_pages)} pages")
 
def should_search_web(question):
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": f"""Does this question require current internet information (trends, news, prices, recent events) or can it be answered from a research report about Canadian mushroom consumers?
 
Question: {question}
 
Reply with only one word: WEB or REPORT"""
        }]
    )
    answer = response.content[0].text.strip().upper()
    return "WEB" in answer
 
def is_mushroom_related(question):
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": f"""Is this question related to mushrooms, mushroom consumption, mushroom shopping, mushroom trends, or mushroom research? Answer only YES or NO.
 
Question: {question}"""
        }]
    )
    answer = response.content[0].text.strip().upper()
    return "YES" in answer
 
def find_relevant_pages(question, max_pages=6):
    """Find the most relevant pages for a question using text search first."""
    if not pdf_pages:
        return []
    keywords = question.lower().split()
    scored = []
    for page in pdf_pages:
        text_lower = page["text"].lower()
        score = sum(1 for kw in keywords if kw in text_lower)
        scored.append((score, page))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [p for _, p in scored[:max_pages]]
    if not top:
        top = pdf_pages[:max_pages]
    return top
 
def build_system_prompt(source):
    base = f"""You are David Chen, a {PERSONA['age']}-year-old Consumer Insights Expert based in {PERSONA['city']}, Ontario with over 20 years of experience in the Canadian produce industry. You know the data inside and out but you speak in plain, conversational language, not like a stiff analyst. You are approachable, direct, and genuinely passionate about produce.
 
You speak in first person, drawing on your professional expertise and years of working with Canadian grocery data and consumer research. You are warm and engaging without being casual. Think of yourself as the smartest person in the room who never makes others feel that way.
 
Keep answers under 150 words unless asked for more detail.
 
IMPORTANT: You only answer questions about mushrooms, mushroom consumers, mushroom trends, or mushroom research. If anyone asks about anything else say warmly: 'That is a great question but mushrooms are my specialty here. Is there anything about the mushroom category I can help you with?'"""
 
    if source == "web":
        return base + """
 
You have just searched the internet for current information. When answering naturally say something like 'I just looked this up and from what I am seeing online...' Then share what you found in your warm personal voice."""
    else:
        return base + """
 
You have been shown pages from a research report about Canadian mushroom consumers including charts, graphs, and written commentary. Read all the visual data and text carefully. When answering naturally say something like 'From the research I have seen on this...' and cite specific numbers and findings from the report pages you have been shown. If the pages shown do not contain the answer, say so honestly and share your personal experience instead."""
 
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
 
    if not is_mushroom_related(user_message):
        return jsonify({
            "reply": "Oh I wish I could help with that, but mushrooms are really my thing! Is there anything mushroom related I can help you with?",
            "source": None,
            "persona": PERSONA
        })
 
    use_web = should_search_web(user_message)
    source = "web" if use_web else "report"
 
    messages = []
 
    if not use_web and pdf_pages:
        relevant_pages = find_relevant_pages(user_message, max_pages=6)
        pdf_context = []
        pdf_context.append({
            "type": "text",
            "text": f"Here are the most relevant pages from the mushroom consumer research report. Please read all text and visual data carefully including charts, percentages, and graphs:"
        })
        for page in relevant_pages:
            pdf_context.append({
                "type": "text",
                "text": f"\n--- Page {page['page']} ---"
            })
            pdf_context.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": page["image_b64"]
                }
            })
            if page["text"].strip():
                pdf_context.append({
                    "type": "text",
                    "text": f"Extracted text from page {page['page']}: {page['text'][:1500]}"
                })
        pdf_context.append({
            "type": "text",
            "text": f"\nNow please answer this question as David, using specific data from the report pages above: {user_message}"
        })
        messages.append({"role": "user", "content": pdf_context})
        messages.append({"role": "assistant", "content": "I have carefully reviewed the research report pages including all charts and visual data. I will answer based on what I can see in them."})
 
    for msg in history[-4:]:
        messages.append(msg)
 
    messages.append({"role": "user", "content": user_message})
 
    try:
        if use_web:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=600,
                system=build_system_prompt("web"),
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=messages
            )
        else:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=600,
                system=build_system_prompt("report"),
                messages=messages
            )
 
        reply = ""
        for block in response.content:
            if block.type == "text":
                reply += block.text
 
        return jsonify({
            "reply": reply,
            "source": source,
            "persona": PERSONA
        })
 
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
    global pdf_pages
    pdf_pages = []
    load_pdf()
    return jsonify({"success": True, "pages": len(pdf_pages)})
 
@app.route("/api/pdf-status", methods=["GET"])
def pdf_status():
    return jsonify({
        "loaded": len(pdf_pages) > 0,
        "pages": len(pdf_pages)
    })
 
load_pdf()
 
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
 
