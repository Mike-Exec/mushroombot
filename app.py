import os
import anthropic
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path

app = Flask(__name__)
CORS(app)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

KNOWLEDGE_PATH = "report_knowledge.txt"
report_knowledge = ""

PERSONA = {
    "name": "David Chen",
    "age": 48,
    "city": "Toronto",
    "description": "Consumer Insights Expert, Canadian Produce Industry",
    "initials": "DC"
}

def load_knowledge():
    global report_knowledge
    if not Path(KNOWLEDGE_PATH).exists():
        print("No knowledge file found")
        return
    with open(KNOWLEDGE_PATH, "r") as f:
        report_knowledge = f.read()
    print(f"Knowledge file loaded: {len(report_knowledge)} characters")

def should_search_web(question):
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": f"""Does this question require current internet information (trends, news, prices, recent events happening now) or can it be answered from a research report about Canadian mushroom consumers?

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
            "content": f"""Is this question related to mushrooms, mushroom consumers, mushroom shopping, mushroom trends, mushroom research, or mushroom cooking? Answer only YES or NO.

Question: {question}"""
        }]
    )
    answer = response.content[0].text.strip().upper()
    return "YES" in answer

def build_system_prompt(source):
    base = f"""You are David Chen, a {PERSONA['age']}-year-old Consumer Insights Expert based in {PERSONA['city']}, Ontario with over 20 years of experience in the Canadian produce industry. You know the data inside and out but you speak in plain, conversational language, not like a stiff analyst. You are approachable, direct, and genuinely passionate about produce.

You speak in first person, drawing on your professional expertise and years of working with Canadian grocery data and consumer research. You are warm and engaging without being casual. Think of yourself as the smartest person in the room who never makes others feel that way.

Keep answers under 150 words unless asked for more detail.

IMPORTANT: You only answer questions about mushrooms, mushroom consumers, mushroom trends, or mushroom research. If anyone asks about anything else say warmly: 'That is a great question but mushrooms are my specialty here. Is there anything about the mushroom category I can help you with?'"""

    if source == "web":
        return base + """

You have just searched the internet for current information. When answering naturally say something like 'I just looked this up and from what I am seeing online...' Then share what you found in your warm professional voice."""
    else:
        if report_knowledge:
            return base + f"""

You have access to the following research data from a Canadian mushroom consumer study conducted by Execulytics Consulting in March 2026 with 1,027 respondents. Use this data to answer questions with specific accurate numbers and findings. When answering say something like 'From the research we conducted...' or 'The data shows...' or 'In our study of 1,027 Canadian consumers...'

RESEARCH DATA:
{report_knowledge}

Always cite specific percentages and numbers from the data above when answering. Do not make up statistics."""
        else:
            return base + """

You are drawing on your professional expertise and knowledge of the Canadian mushroom market. Note that the research report has not been loaded yet, so answer from your general industry knowledge."""

@app.route("/")
def index():
    return send_from_directory(".", "widget.html")

@app.route("/consumer-voice")
def consumer_voice():
    return send_from_directory(".", "consumer_voice.html")

@app.route("/consumer_data.json")
def consumer_data():
    return send_from_directory(".", "consumer_data.json")

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
            "reply": "That is a great question but mushrooms are my specialty here. Is there anything about the mushroom category I can help you with?",
            "source": None,
            "persona": PERSONA
        })

    use_web = should_search_web(user_message)
    source = "web" if use_web else "report"

    messages = []
    for msg in history[-6:]:
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

@app.route("/api/knowledge-status", methods=["GET"])
def knowledge_status():
    return jsonify({
        "loaded": len(report_knowledge) > 0,
        "characters": len(report_knowledge)
    })

load_knowledge()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
