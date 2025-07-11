import os, json, traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from fuzzywuzzy import process
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise RuntimeError("GOOGLE_API_KEY not set!")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash:generateContent")

app = Flask(__name__)
CORS(app)

with open("inventory.json") as f:
    INVENTORY = json.load(f)
    NAMES = [i["name"].lower() for i in INVENTORY]

def match_item(name):
    best, _ = process.extractOne(name.lower(), NAMES)
    return next((i for i in INVENTORY if i["name"].lower() == best), None)

@app.route("/generate-meal", methods=["POST"])
@app.route("/generate-meal", methods=["POST"])
def generate_meal():
    data = request.json
    prompt = f"""
Plan a {data['diet']} dinner for {data['servings']} under ₹{data['budget']}
using only ingredients available at Walmart. Avoid {data['restrictions']}.
Must be cooked in under {data['time_limit']}.
Respond ONLY with valid JSON:
{{
  "meal_name": "...",
  "ingredients": [{{"name":"...","quantity":"..."}}, ...],
  "instructions": ["step1","step2",...]
}}
"""

    try:
        resp = model.generate_content(prompt)
        text = resp.candidates[0].content.parts[0].text
        print("🔍 RAW RESPONSE FROM GEMINI:")
        print(text)  # Print for debugging

        meal = json.loads(text)

    except Exception as e:
        traceback.print_exc()
        return jsonify(error="AI error", raw=text if 'text' in locals() else str(e)), 500

    cart, total = [], 0
    for ing in meal["ingredients"]:
        itm = match_item(ing["name"])
        if itm:
            cart.append({**ing, "price": itm["price"]})
            total += itm["price"]

    return jsonify({**meal, "cart": cart, "total": total})


if __name__ == "__main__":
    app.run(debug=True)
