import os
import json
import random
import string
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
from fuzzywuzzy import process as fuzzy_process

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY not set in .env")
genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app)

PROFILE_PATH = "profile_001.json"

# Ensure profile and products files exist
if not os.path.exists("profile_001.json"):
    with open("profile_001.json", "w") as f:
        json.dump({"allergies": [], "preferences": []}, f)
if not os.path.exists("utils/products.json"):
    os.makedirs("utils", exist_ok=True)
    with open("utils/products.json", "w") as f:
        json.dump([], f)

# Load products and stores from root
with open("utils/products.json") as f:
    PRODUCTS = json.load(f)
with open("utils/stores.json") as f:
    STORES = json.load(f)

sku_to_product = {p["sku"]: p for p in PRODUCTS}
name_to_sku = {p["name"].lower(): p["sku"] for p in PRODUCTS}

# Helper: Call Google Gemini to parse user input into structured profile
def parse_profile_with_gemini(user_input):
    prompt = f'''
You are an expert AI assistant for Walmart. Your job is to convert a user's free-form description of their food preferences, allergies, and shopping habits into a structured JSON profile.

Return valid JSON. All property names and string values must use double quotes ("). Do n ot use single quotes or Python dicts.

Example output:
{{
  "diet": ["vegetarian"],
  "allergies": ["peanuts"],
  "preferences": ["budget", "organic"],
  "shoppingFrequency": "weekly",
  "household": 2
}}

User input: "{user_input}"

JSON profile:
'''
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text.strip()
        print(f"[DEBUG] Raw Gemini response: {repr(text)}")  # Log raw response

        # Remove Markdown code block if present
        if text.startswith('```'):
            lines = text.splitlines()
            # Remove the first line (``` or ```json)
            if lines[0].strip().startswith('```'):
                lines = lines[1:]
            # Remove the last line if it's ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            text = '\n'.join(lines).strip()
        print(f"[DEBUG] Cleaned Gemini response: {repr(text)}")  # Log cleaned response

        if not text:
            print("[ERROR] Gemini returned an empty response after cleaning.")
            return None, "Gemini returned an empty response. Please try again or rephrase your input."
        import re
        try:
            profile = json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON substring if extra text is present
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                json_str = match.group(0)
                try:
                    profile = json.loads(json_str)
                except json.JSONDecodeError:
                    # Fallback: replace single quotes with double quotes
                    fixed = json_str.replace("'", '"')
                    try:
                        profile = json.loads(fixed)
                    except Exception as e2:
                        print(f"[ERROR] Could not parse JSON from Gemini response after fixing quotes: {fixed}")
                        return None, f"Could not parse JSON from Gemini response: {text} | Error: {e2}"
                except Exception as e2:
                    print(f"[ERROR] Could not parse JSON from Gemini response: {json_str}")
                    return None, f"Could not parse JSON from Gemini response: {text} | Error: {e2}"
            else:
                print(f"[ERROR] Could not find JSON in Gemini response: {text}")
                return None, f"Could not parse JSON from Gemini response: {text}"
        return profile, None
    except Exception as e:
        print(f"[EXCEPTION] Gemini API call failed: {e}")
        import traceback; traceback.print_exc()
        return None, f"Gemini API call failed: {e}"

# Helper: Recursively extract allergies and preferences from any location in the profile

def extract_allergies_preferences(profile):
    allergies = set()
    preferences = set()
    def recurse(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k.lower() == "allergies" and isinstance(v, list):
                    allergies.update(a.lower().replace(" allergy", "").strip() for a in v)
                if k.lower() == "preferences" and isinstance(v, list):
                    preferences.update(p.lower() for p in v)
                recurse(v)
        elif isinstance(obj, list):
            for item in obj:
                recurse(item)
    recurse(profile)
    return allergies, preferences

@app.route("/health", methods=["GET"])
def health():
    print("[LOG] /health endpoint called")
    return jsonify({"status": "ok"})

@app.route("/profile", methods=["POST"])
def profile():
    print("[LOG] /profile POST endpoint called")
    try:
        data = request.get_json()
        user_input = data.get("userInput")
        if not user_input:
            print("[ERROR] Missing userInput in /profile POST")
            return jsonify({"error": "Missing userInput"}), 400
        profile, error = parse_profile_with_gemini(user_input)
        if error:
            print(f"[ERROR] AI parsing failed: {error}")
            return jsonify({"error": f"AI parsing failed: {error}"}), 500
        # Save profile to local file
        try:
            with open(PROFILE_PATH, "w") as f:
                json.dump(profile, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save profile: {e}")
            return jsonify({"error": f"Failed to save profile: {e}"}), 500
        print("[LOG] /profile POST success")
        return jsonify({"profile": profile})
    except Exception as e:
        print(f"[EXCEPTION] /profile POST: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/profile", methods=["GET"])
def get_profile():
    print("[LOG] /profile GET endpoint called")
    try:
        if not os.path.exists(PROFILE_PATH):
            print("[ERROR] No profile found in /profile GET")
            return jsonify({"error": "No profile found"}), 404
        with open(PROFILE_PATH) as f:
            profile = json.load(f)
        print("[LOG] /profile GET success")
        return jsonify({"profile": profile})
    except Exception as e:
        print(f"[EXCEPTION] /profile GET: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/profile", methods=["DELETE"])
def delete_profile():
    print("[LOG] /profile DELETE endpoint called")
    try:
        import os
        if os.path.exists(PROFILE_PATH):
            os.remove(PROFILE_PATH)
        return jsonify({"success": True})
    except Exception as e:
        print(f"[ERROR] Failed to delete profile: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/process-cart", methods=["POST"])
def process_cart():
    print("[LOG] /process-cart POST endpoint called")
    try:
        data = request.get_json()
        shopping_list = data.get("shoppingList", [])
        profile = data.get("profile", {})

        # Normalize shopping_list: accept both strings and dicts
        normalized_list = []
        for item in shopping_list:
            if isinstance(item, dict) and "name" in item:
                normalized_list.append(item["name"])
            elif isinstance(item, str):
                normalized_list.append(item)
            else:
                continue  # skip invalid items
        shopping_list = normalized_list

        # Robustly extract allergies and preferences from any location
        allergies, preferences = extract_allergies_preferences(profile)

        # Load product catalog, allergen dict, and substitutions
        with open("utils/products.json") as f:
            products_list = json.load(f)
            products = {p["name"].lower(): p for p in products_list}
            product_names = [p["name"].lower() for p in products_list]
        with open("utils/allergens.json") as f:
            allergen_dict = json.load(f)
        with open("utils/substitutions.json") as f:
            substitutions = json.load(f)

        cart = []
        for item in shopping_list:
            item_lc = item.lower()
            product = products.get(item_lc)
            # Fuzzy match if not found
            if not product:
                best_match, score = fuzzy_process.extractOne(item_lc, product_names)
                if score > 80:
                    product = products.get(best_match)
            flagged = False
            warned = False
            reason = ""
            status = "Safe"
            safe_alt = None
            # Check for allergy risk
            if product:
                for allergy in allergies:
                    for allergen in product.get("allergens", []):
                        from fuzzywuzzy import fuzz
                        if (
                            allergy == allergen.lower() or
                            any(allergy == k and allergen.lower() in v for k, v in allergen_dict.items()) or
                            fuzz.ratio(allergy, allergen.lower()) > 80
                        ):
                            flagged = True
                            status = "Risk"
                            reason = f"Contains {allergen}, which matches your allergy or restriction: {allergy}."
                            break
                    if flagged:
                        break
                # Check for preferences (warn only, not risk)
                if not flagged:
                    for pref in preferences:
                        if any(pref in allergen.lower() or pref in item_lc for allergen in product.get("allergens", []) + [item_lc]):
                            warned = True
                            status = "Warn"
                            reason = f"You said you dislike or want to avoid {item}."
                            break
            # Suggest safe alternative if risky and available
            if flagged and item_lc in substitutions:
                safe_alt = substitutions[item_lc]["safeAlt"]
                status = "Substituted"
                reason = substitutions[item_lc]["reason"]
            cart.append({
                "original": item,
                "status": status,
                "safeAlternative": safe_alt,
                "reason": reason
            })
        print("[LOG] /process-cart POST success")
        return jsonify({"cart": cart})
    except Exception as e:
        print(f"[EXCEPTION] /process-cart POST: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/pickup-suggestion", methods=["POST"])
def pickup_suggestion():
    print("[LOG] /pickup-suggestion POST endpoint called")
    try:
        data = request.json
        cart = data.get("cart", [])
        if not cart:
            print("[ERROR] No cart provided in /pickup-suggestion POST")
            return jsonify(error="No cart provided"), 400

        # Normalize cart: accept both strings and dicts
        normalized_cart = []
        for item in cart:
            if isinstance(item, dict) and "name" in item:
                normalized_cart.append(item["name"])
            elif isinstance(item, str):
                normalized_cart.append(item)
            else:
                continue  # skip invalid items
        cart = normalized_cart

        # Normalize cart to SKUs, track not found items
        cart_skus = []
        not_found_items = []
        for item in cart:
            if item in sku_to_product:
                cart_skus.append(item)
            elif isinstance(item, str) and item.lower() in name_to_sku:
                cart_skus.append(name_to_sku[item.lower()])
            else:
                best, score = fuzzy_process.extractOne(str(item), list(name_to_sku.keys()))
                if score > 80:
                    cart_skus.append(name_to_sku[best])
                else:
                    not_found_items.append(item)

        # Find best store
        best_store = None
        best_count = -1
        packed, missing = [], []
        for store, info in STORES.items():
            available = set(info["availableSKUs"])
            packed_here = [sku for sku in cart_skus if sku in available]
            if len(packed_here) > best_count:
                best_store = store
                best_count = len(packed_here)
                packed = packed_here
        # Compute missing
        if best_store:
            available = set(STORES[best_store]["availableSKUs"])
            missing = [sku for sku in cart_skus if sku not in available]
        else:
            missing = cart_skus

        packed_items = [sku_to_product[sku] for sku in packed]
        missing_items = [sku_to_product[sku] for sku in missing if sku in sku_to_product]
        pickup_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        # --- Find nearest store for each missing item ---
        nearest_stores_for_missing = {}
        for missing_item in missing_items:
            sku = missing_item['sku']
            nearest_store = None
            for store, info in STORES.items():
                if store == best_store:
                    continue
                if sku in info['availableSKUs']:
                    nearest_store = {
                        'name': store,
                        'address': info.get('address', '')
                    }
                    break  # Take the first found (could add distance logic)
            if nearest_store:
                nearest_stores_for_missing[missing_item['name']] = nearest_store

        # Logging for analytics
        print(f"[ANALYTICS] Store selected: {best_store}")
        print(f"[ANALYTICS] Packed items: {[p['name'] for p in packed_items]}")
        print(f"[ANALYTICS] Missing items: {[m['name'] for m in missing_items]}")
        print(f"[ANALYTICS] Not found items: {not_found_items}")

        # Build store details (name, address, lat, lon)
        store_details = None
        if best_store:
            store_info = STORES[best_store]
            store_details = {
                "name": best_store,
                "address": store_info.get("address"),
                "lat": store_info.get("lat"),
                "lon": store_info.get("lon")
            }
        print("[LOG] /pickup-suggestion POST success")
        return jsonify({
            "store": store_details,
            "packed_items": packed_items,
            "missing_items": missing_items,
            "not_found_items": not_found_items,
            "pickup_code": pickup_code,
            "nearest_stores_for_missing": nearest_stores_for_missing
        })
    except Exception as e:
        print(f"[EXCEPTION] /pickup-suggestion POST: {e}")
        import traceback; traceback.print_exc()
        return jsonify(error=str(e)), 500

@app.route("/place-order", methods=["POST"])
def place_order():
    print("[LOG] /place-order POST endpoint called")
    try:
        data = request.get_json()
        cart = data.get("cart", [])
        quantities = data.get("quantities", {})
        store = data.get("store", {})
        pickup_code = data.get("pickup_code", None)
        profile = data.get("profile", {})
        if not cart or not store or not pickup_code:
            return jsonify({"error": "Missing required order fields."}), 400
        order = {
            "order_id": ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)),
            "cart": cart,
            "quantities": quantities,
            "store": store,
            "pickup_code": pickup_code,
            "profile": profile
        }
        orders_path = "orders.json"
        try:
            if os.path.exists(orders_path):
                with open(orders_path, "r") as f:
                    orders = json.load(f)
            else:
                orders = []
        except Exception as e:
            print(f"[ERROR] Reading orders.json: {e}")
            orders = []
        orders.append(order)
        try:
            with open(orders_path, "w") as f:
                json.dump(orders, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Writing orders.json: {e}")
            return jsonify({"error": "Failed to save order."}), 500
        print(f"[LOG] Order placed: {order['order_id']}")
        return jsonify({"success": True, "order_id": order["order_id"]})
    except Exception as e:
        print(f"[EXCEPTION] /place-order POST: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/scan-qr/", methods=["POST"])
def scan_qr():
    '''
    Accepts JSON: {"sku": <sku string>}
    Returns product info, safety analysis, and alternatives based on profile_001.json
    '''
    try:
        data = request.get_json()
        sku = data.get("sku")
        if not sku:
            return jsonify({"error": "Missing SKU"}), 400
        # Load user profile
        if not os.path.exists("profile_001.json"):
            return jsonify({"error": "No user profile found"}), 404
        with open("profile_001.json") as f:
            profile = json.load(f)
        allergies = set(a.lower() for a in profile.get("allergies", []))
        preferences = set(p.lower() for p in profile.get("preferences", []))
        # Load products
        with open("utils/products.json") as f:
            products = json.load(f)
        product = next((p for p in products if p["sku"] == sku), None)
        if not product:
            return jsonify({"error": "Product not found for SKU"}), 404
        # Safety analysis
        product_allergens = set(a.lower() for a in product.get("allergens", []))
        is_safe = not (allergies & product_allergens)
        flagged_allergens = list(allergies & product_allergens)
        # Find up to 2 safe alternatives
        alternatives = []
        for alt in products:
            if alt["sku"] == sku:
                continue
            alt_allergens = set(a.lower() for a in alt.get("allergens", []))
            if not (allergies & alt_allergens):
                alternatives.append({
                    "name": alt["name"],
                    "sku": alt["sku"],
                    "price": alt["price"],
                    "tags": alt.get("tags", []),
                    "rating": alt.get("rating", None)
                })
            if len(alternatives) >= 2:
                break
        # Build response
        result = {
            "product": {
                "name": product["name"],
                "sku": product["sku"],
                "price": product["price"],
                "allergens": product.get("allergens", []),
                "tags": product.get("tags", []),
                "rating": product.get("rating", None)
            },
            "is_safe": is_safe,
            "flagged_allergens": flagged_allergens,
            "alternatives": alternatives
        }
        return jsonify(result)
    except Exception as e:
        print(f"[EXCEPTION] /scan-qr/: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5050)