# client/app.py

import streamlit as st
import requests
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
import qrcode
from io import BytesIO
import re

# --- ENV & CONFIG ---
load_dotenv()
API_URL = "http://localhost:5050"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(page_title="SmartCart — Walmart's Neuro-AI Concierge", page_icon="🛒", layout="centered")
st.title("SmartCart — Walmart's Neuro-AI Concierge")
st.markdown("💬 **Conversational, allergy-aware, and built for modern shoppers.**")
st.markdown("──────────────────────────────")

# --- Gemini Profile Logic ---
load_dotenv()
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    st.error("Error configuring Gemini API: {}".format(e))
    st.stop()

def parse_gemini_json(text):
    text = text.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        if lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines).strip()
    return text

# --- AI Function with Update Logic ---
def get_or_update_walmart_profile(user_input: str, existing_profile: dict = None) -> dict:
    model = genai.GenerativeModel('gemini-1.5-flash')
    if existing_profile:
        prompt = f'''You are an expert AI profiling assistant for Walmart. Your task is to intelligently update a customer's profile with new information.\n\nYou will be given the customer's CURRENT profile as a JSON object and a NEW piece of text from the customer.\n\nAnalyze the NEW text and merge the information into the CURRENT profile.\n- You may need to ADD new keys or objects (e.g., a new dietary need, a new interest).\n- You may need to MODIFY existing values (e.g., changing family size, updating shopping frequency).\n\nReturn the SINGLE, COMPLETE, and UPDATED JSON object. Do not add conversational text or markdown outside of the final JSON.\n\nCURRENT Profile:\n{json.dumps(existing_profile, indent=2)}\n\nNEW User Input:\n"{user_input}"\n\nUPDATED JSON Output:\n'''
    else:
        prompt = f'''You are an expert AI profiling assistant for Walmart. Your primary goal is to create a detailed and actionable customer profile from a user's conversational description.\n\nAnalyze the following text and extract all information that would help Walmart understand this customer's needs, lifestyle, and shopping patterns. Organize your findings into a structured JSON object.\n\nCreate logical categories relevant to retail (e.g., "household_profile", "shopping_behavior", "product_interests", "lifestyle_and_hobbies", "dietary_needs").\n\nStrictly respond with a single JSON object.\n\nUser Input: "{user_input}"\n\nJSON Output:\n'''
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1
            )
        )
        cleaned = parse_gemini_json(response.text)
        if not cleaned:
            st.error("Gemini returned an empty response. Please try again or rephrase your request.")
            st.write("Gemini's raw response:")
            st.code(response.text)
            return {"error": "Empty response", "raw_response": response.text}
        parsed_json = json.loads(cleaned)
        return parsed_json
    except json.JSONDecodeError as e:
        st.error(f"Failed to decode JSON from Gemini. Error: {e}")
        st.write("Gemini's raw response:")
        st.code(response.text)
        return {"error": "JSON parsing failed", "raw_response": response.text}
    except Exception as e:
        st.error(f"An error occurred during Gemini API call: {e}")
        return {"error": str(e)}

# --- SESSION STATE ---
if "profile_data" not in st.session_state or st.session_state.profile_data is None:
    try:
        resp = requests.get(f"{API_URL}/profile")
        if resp.status_code == 200:
            st.session_state.profile_data = resp.json().get("profile")
    except Exception:
        pass  # It's okay if not found yet
if "stores_data" not in st.session_state or st.session_state.stores_data is None:
    import json
    try:
        # Try to fetch from backend if you have an endpoint, else load from file
        with open("utils/stores.json", "r") as f:
            st.session_state.stores_data = json.load(f)
    except Exception:
        st.session_state.stores_data = None
if "cart_data" not in st.session_state:
    st.session_state.cart_data = None
if "final_cart" not in st.session_state:
    st.session_state.final_cart = []
if "handled_items" not in st.session_state:
    st.session_state.handled_items = set()
if "cart_choices" not in st.session_state:
    st.session_state.cart_choices = {}
if "show_cart_review" not in st.session_state:
    st.session_state.show_cart_review = False
if "cart_processed" not in st.session_state:
    st.session_state.cart_processed = False

# --- TABS ---
tabs = st.tabs(["Profile", "Cart", "Pickup"])

# --- PROFILE TAB ---
with tabs[0]:
    st.markdown("### 🔹 Section 1: Personalizing Your SmartCart 🧠")
    st.write(
        """
Let’s begin by understanding your needs, your household, and what matters most when you shop.

This GenAI assistant will convert your description into a personalized customer profile — detecting allergies, dietary preferences, budget goals, and more.
"""
    )
    if st.session_state.profile_data:
        st.success("A customer profile is active. You can now provide updates.")
        st.subheader("Current Customer Profile")
        st.json(st.session_state.profile_data)
        st.markdown("---")
        update_input = st.text_area(
            "What's new? (e.g., 'I've recently become vegetarian', or 'We're planning a birthday party for a 10-year-old')",
            key="update_text"
        )
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Update Profile", use_container_width=True):
                if update_input:
                    with st.spinner("🧠 Updating your profile with new info..."):
                        updated_profile = get_or_update_walmart_profile(update_input, st.session_state.profile_data)
                        if "error" not in updated_profile:
                            st.session_state.profile_data = updated_profile
                            # Optionally, POST to backend to persist
                            try:
                                requests.post(f"{API_URL}/profile", json={"userInput": json.dumps(updated_profile)})
                            except Exception:
                                pass
                            st.rerun()
                else:
                    st.warning("Please enter an update.")
        with col2:
            if st.button("Clear Profile & Start Over", type="primary", use_container_width=True):
                st.session_state.profile_data = None
                try:
                    requests.delete(f"{API_URL}/profile", timeout=10)
                except Exception:
                    pass
                st.rerun()
    else:
        profile_input = st.text_area(
            "🧑‍💬 In your own words, tell me about your shopping preferences, allergies, or lifestyle:",
            placeholder="E.g., I’m allergic to peanuts and I’m a budget-conscious student. I mostly buy plant-based meals and prefer Walmart’s pickup option. I avoid crowded stores and check for sustainable or vegan alternatives.",
            height=120,
            key="profile_input_box"
        )
        if st.button("🔍 Analyze & Build My SmartCart Profile"):
            if profile_input.strip():
                with st.spinner("Analyzing your preferences and building your profile..."):
                    profile = get_or_update_walmart_profile(profile_input, None)
                    if "error" not in profile:
                        st.session_state.profile_data = profile
                        # Optionally, POST to backend to persist
                        try:
                            requests.post(f"{API_URL}/profile", json={"userInput": json.dumps(profile)})
                        except Exception:
                            pass
                        st.rerun()
                    else:
                        st.error(profile.get("error", "Unknown error"))
            else:
                st.warning("Please enter a description to generate your profile.")

# --- CART TAB ---
with tabs[1]:
    st.header("2️⃣ Smart Cart & Allergy-Safe Substitution")
    if not st.session_state.profile_data:
        st.warning("No profile found. Please complete onboarding first (see Profile tab).")
        st.stop()
    st.markdown("Paste your shopping list or just chat with the bot about what you want to buy. AI will flag risky items and suggest safe alternatives!")
    input_mode = st.radio("How would you like to add items?", ["Chat with Bot", "Paste Shopping List"], horizontal=True)
    shopping_items = []
    def reset_cart_state():
        st.session_state.cart_data = None
        st.session_state.final_cart = []
        st.session_state.handled_items = set()
        st.session_state.cart_choices = {}
        st.session_state.show_cart_review = False
        st.session_state.cart_processed = False
        st.session_state.pickup_cart = []  # Always clear pickup_cart on new cart
    if input_mode == "Chat with Bot":
        chat_input = st.text_area(
            "Describe what you want to buy (e.g. 'I need peanut butter, oat milk, and some bread for sandwiches'):",
            height=100,
            placeholder="I need peanut butter, oat milk, and some bread for sandwiches."
        )
        if st.button("Generate Smart Cart from Chat 🪄") and chat_input.strip():
            with st.spinner("Extracting shopping list from your chat using Gemini..."):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f'''Extract a shopping list from this message. Return only a JSON array of distinct, real-world grocery items (no grouping, no product name combinations, no extra text):\n\n"{chat_input}"'''
                    response = model.generate_content(prompt)
                    text = response.text.strip()
                    text = parse_gemini_json(text)
                    if not text:
                        st.error("Gemini returned an empty response. Please try again or rephrase your request.")
                        shopping_items = []
                    else:
                        try:
                            shopping_items = json.loads(text)
                            # --- Post-process: split combined items if needed ---
                            processed_items = []
                            known_items = ["peanut butter", "pasta", "bread", "oat milk", "milk", "cheese", "eggs", "rice", "beans", "tofu", "tempeh", "lentils"]
                            for item in shopping_items:
                                if isinstance(item, str):
                                    lower_item = item.lower()
                                    # Split on 'and', '&', ',' if present
                                    if any(sep in lower_item for sep in [',', ' and ', ' & '] ):
                                        for part in re.split(r',| and | & ', lower_item):
                                            part = part.strip()
                                            if part and part not in processed_items:
                                                processed_items.append(part)
                                    # Split known combos (e.g., 'peanut butter pasta')
                                    elif 'peanut butter' in lower_item and 'pasta' in lower_item:
                                        if 'peanut butter' not in processed_items:
                                            processed_items.append('peanut butter')
                                        if 'pasta' not in processed_items:
                                            processed_items.append('pasta')
                                    else:
                                        if item not in processed_items:
                                            processed_items.append(item)
                                else:
                                    processed_items.append(item)
                            shopping_items = processed_items
                        except json.JSONDecodeError:
                            import re
                            match = re.search(r'\[.*\]', text, re.DOTALL)
                            if match:
                                try:
                                    shopping_items = json.loads(match.group(0))
                                except Exception as e2:
                                    st.error(f"Could not parse shopping list from Gemini: {text}")
                                    st.write("Raw Gemini output:")
                                    st.code(text)
                                    shopping_items = []
                            else:
                                st.error(f"Could not parse shopping list from Gemini: {text}")
                                st.write("Raw Gemini output:")
                                st.code(text)
                                shopping_items = []
                except Exception as e:
                    st.error(f"Gemini request failed: {e}")
                    shopping_items = []
            if shopping_items:
                reset_cart_state()
                with st.spinner("Processing your cart and checking for allergy risks..."):
                    try:
                        resp = requests.post(
                            f"{API_URL}/process-cart",
                            json={"shoppingList": shopping_items, "profile": st.session_state.profile_data},
                            timeout=60
                        )
                        if resp.status_code == 200:
                            cart = resp.json()["cart"]
                            st.session_state.cart_data = cart
                        else:
                            error_msg = resp.json().get('error', 'Unknown error')
                            st.error(f'Error: {error_msg}')
                    except Exception as e:
                        st.error(f"Request failed: {e}")
    else:
        shopping_list = st.text_area(
            "Enter your shopping list (one item per line):",
            height=120,
            placeholder="peanut butter\ngluten-free bread\noat milk"
        )
        if st.button("Build My Smart Cart 🛒") and shopping_list.strip():
            shopping_items = [line.strip() for line in shopping_list.splitlines() if line.strip()]
            if shopping_items:
                reset_cart_state()
                with st.spinner("Processing your cart and checking for allergy risks..."):
                    try:
                        resp = requests.post(
                            f"{API_URL}/process-cart",
                            json={"shoppingList": shopping_items, "profile": st.session_state.profile_data},
                            timeout=60
                        )
                        if resp.status_code == 200:
                            cart = resp.json()["cart"]
                            st.session_state.cart_data = cart
                        else:
                            error_msg = resp.json().get('error', 'Unknown error')
                            st.error(f'Error: {error_msg}')
                    except Exception as e:
                        st.error(f"Request failed: {e}")
    # --- Cart Rendering ---
    if st.session_state.get('cart_data'):
        cart = st.session_state.cart_data
        st.header("🧾 Your Smart Cart (Conversational)")
        # Batch actions for alternatives
        if any(entry.get('status') == 'Substituted' for entry in cart):
            colA, colB = st.columns([1,1])
            with colA:
                if st.button('Accept All Alternatives', key='accept_all'):
                    for entry in cart:
                        if entry.get('status') == 'Substituted' and entry['original'] not in st.session_state.handled_items:
                            alt = entry.get('safeAlternative')
                            if alt not in st.session_state.final_cart:
                                st.session_state.final_cart.append(alt)
                            st.session_state.handled_items.add(entry['original'])
                            st.session_state.cart_choices[entry['original']] = 'accept'
                    st.rerun()
            with colB:
                if st.button('Reject All Alternatives', key='reject_all'):
                    for entry in cart:
                        if entry.get('status') == 'Substituted' and entry['original'] not in st.session_state.handled_items:
                            if entry['original'] not in st.session_state.final_cart:
                                st.session_state.final_cart.append(entry['original'])
                            st.session_state.handled_items.add(entry['original'])
                            st.session_state.cart_choices[entry['original']] = 'reject'
                    st.rerun()
        for idx, entry in enumerate(cart):
            item = entry['original']
            status = entry.get('status', 'unknown')
            alt = entry.get('safeAlternative')
            reason = entry.get('reason', '')
            key_accept = f"accept_{idx}_{item}_{status}"
            key_reject = f"reject_{idx}_{item}_{status}"
            already_handled = item in st.session_state.handled_items
            if status == "Safe":
                st.success(f"✅ Great news! **{item}** is safe for you.")
                if not already_handled and item not in st.session_state.final_cart:
                    st.session_state.final_cart.append(item)
                    st.session_state.handled_items.add(item)
                    st.session_state.cart_choices[item] = 'safe'
            elif status == "Warn":
                st.warning(f"⚠️ Note: You said you dislike or want to avoid **{item}**. {reason}")
                if not already_handled and item not in st.session_state.final_cart:
                    st.session_state.final_cart.append(item)
                    st.session_state.handled_items.add(item)
                    st.session_state.cart_choices[item] = 'warn'
            elif status == "Substituted":
                st.warning(f"⚠️ Heads up! **{item}** is risky for you. We suggest **{alt}** instead. Reason: {reason}")
                col1, col2 = st.columns([1,1])
                with col1:
                    if st.button("Accept", key=key_accept, disabled=already_handled):
                        if alt not in st.session_state.final_cart:
                            st.session_state.final_cart.append(alt)
                        st.session_state.handled_items.add(item)
                        st.session_state.cart_choices[item] = 'accept'
                        st.rerun()
                with col2:
                    if st.button("Reject", key=key_reject, disabled=already_handled):
                        if item not in st.session_state.final_cart:
                            st.session_state.final_cart.append(item)
                        st.session_state.handled_items.add(item)
                        st.session_state.cart_choices[item] = 'reject'
                        st.rerun()
            elif status == "Risk":
                st.error(f"❌ Caution: **{item}** is risky for you. {reason}")
                if not already_handled and item not in st.session_state.final_cart:
                    st.session_state.final_cart.append(item)
                    st.session_state.handled_items.add(item)
                    st.session_state.cart_choices[item] = 'risk'
            else:
                st.info(f"ℹ️ {item}: {status}. {reason}")
                if not already_handled and item not in st.session_state.final_cart:
                    st.session_state.final_cart.append(item)
                    st.session_state.handled_items.add(item)
                    st.session_state.cart_choices[item] = status
        # If all items are handled, show Go to Cart button
        all_handled = all(entry['original'] in st.session_state.handled_items for entry in cart)
        if all_handled and not st.session_state.show_cart_review:
            if st.button('Go to Cart'):
                st.session_state.show_cart_review = True
                st.rerun()
        # Cart Review Section
        if st.session_state.show_cart_review:
            st.markdown('---')
            st.markdown('### 🛒 Review Your Cart')
            if st.session_state.final_cart:
                st.write(f"**{len(st.session_state.final_cart)} items in your cart:**")
                # --- Initialize or update cart_quantities dict ---
                if 'cart_quantities' not in st.session_state:
                    st.session_state['cart_quantities'] = {item: 1 for item in st.session_state.final_cart}
                else:
                    for item in st.session_state.final_cart:
                        if item not in st.session_state['cart_quantities']:
                            st.session_state['cart_quantities'][item] = 1
                    for item in list(st.session_state['cart_quantities'].keys()):
                        if item not in st.session_state.final_cart:
                            del st.session_state['cart_quantities'][item]
                # --- Custom CSS for modern cart row ---
                st.markdown("""
                <style>
                .cart-row-modern { display: flex; align-items: center; justify-content: space-between; background: #181818; border-radius: 12px; padding: 18px 24px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.12); }
                .cart-item-name-modern { color: #fff; font-size: 18px; font-weight: 500; display: flex; align-items: center; }
                .qty-inline { display: flex; align-items: center; gap: 10px; }
                .qty-label-modern { color: #bbb; font-size: 15px; margin-right: 8px; }
                .qty-input-modern input { border-radius: 8px; border: 1px solid #333; background: #222; color: #fff; font-size: 17px; padding: 6px 12px; box-shadow: 0 1px 4px rgba(0,0,0,0.10); width: 60px; }
                .remove-btn-modern { background: #23272b; color: #fff; border: none; border-radius: 8px; padding: 8px 18px; font-size: 17px; margin-left: 18px; cursor: pointer; display: flex; align-items: center; transition: background 0.2s; }
                .remove-btn-modern:hover { background: #3a3f44; color: #ff5252; }
                .confirm-btn { background: #0071ce; color: #fff; border: none; border-radius: 12px; font-size: 19px; font-weight: 600; width: 100%; padding: 18px 0; margin-top: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.10); transition: background 0.2s, box-shadow 0.2s; }
                .confirm-btn:hover { background: #005fa3; box-shadow: 0 4px 16px rgba(0,113,206,0.18); }
                </style>
                """, unsafe_allow_html=True)
                # --- Render cart items ---
                for idx, item in enumerate(st.session_state.final_cart):
                    # Only render the cart row if the item is not empty
                    if item:
                        st.markdown(f'<div class="cart-row-modern">'
                                    f'<div class="cart-item-name-modern">🛒 {item.title()}</div>'
                                    f'<div class="qty-inline">'
                                    f'<span class="qty-label-modern">Qty</span>', unsafe_allow_html=True)
                        qty = st.number_input(
                            f"Quantity for {item}",
                            min_value=1,
                            max_value=99,
                            value=st.session_state['cart_quantities'][item],
                            key=f"qty_{item}",
                            label_visibility="collapsed"
                        )
                        st.session_state['cart_quantities'][item] = qty
                        if st.button("🗑 Remove", key=f"remove_{idx}", help="Remove this item", use_container_width=False):
                            st.session_state.final_cart.pop(idx)
                            st.rerun()
                        st.markdown('</div></div>', unsafe_allow_html=True)
                # --- Confirm button (only once, styled) ---
                confirm_btn_css = '<style>div[data-testid="stButton"] button.confirm-btn {width: 100%; background: #0071ce; color: #fff; border-radius: 12px; font-size: 19px; font-weight: 600; padding: 18px 0; margin-top: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.10);} div[data-testid="stButton"] button.confirm-btn:hover {background: #005fa3;}</style>'
                st.markdown(confirm_btn_css, unsafe_allow_html=True)
                if st.button("🧾 Confirm Cart & Proceed to Pickup", key="confirm_cart_btn", use_container_width=True, help="Confirm your cart and proceed to pickup", type="primary"):
                    st.session_state['pickup_cart'] = st.session_state.final_cart.copy()
                    st.session_state['pickup_quantities'] = st.session_state['cart_quantities'].copy()
                    st.success('Proceeding to store matching and pickup stage!')
            else:
                st.info("Your cart is empty.")
        # If user has made choices, show the final cart
        if st.session_state.final_cart:
            st.markdown("---")
            st.markdown("### 🛒 Your Final Cart")
            st.write(st.session_state.final_cart)

# --- PICKUP TAB ---
with tabs[2]:
    st.header("3️⃣ Store Matching & Pickup")

    # --- Always show QR code if order placed ---
    if st.session_state.get('pickup_order_placed', False):
        data = st.session_state.get('pickup_data')
        order_id = st.session_state.get('order_id')
        if not data:
            st.error("No pickup data found. Please get a pickup suggestion first.")
        else:
            pickup_code = data.get('pickup_code')
            store = data.get('store')
            if not pickup_code:
                st.error("No pickup code found in the pickup data. Please try again.")
            else:
                import qrcode
                import io
                qr = qrcode.make(pickup_code)
                buf = io.BytesIO()
                qr.save(buf, format='PNG')
                st.markdown("#### Show this QR code at the designated Walmart+ counter to collect your order:")
                st.image(buf.getvalue(), width=200)
                # st.success("Order placed! Show this QR code at the store to pick up your order.")
                if store:
                    st.markdown(f"**Store:** {store.get('name', 'N/A')}")
                    st.markdown(f"**Address:** {store.get('address', 'N/A')}")
                    if store.get('lat') and store.get('lon'):
                        gmap_url = f"https://www.google.com/maps/search/?api=1&query={store['lat']},{store['lon']}"
                        st.markdown(f"[📍 Open in Google Maps]({gmap_url})")
                if order_id:
                    st.info(f"**Order ID:** `{order_id}`. Please save this for your records.")
                if st.button("View My Order", key="view_order_btn"):
                    st.json({
                        "Order ID": order_id,
                        "Cart": st.session_state.get('pickup_cart', []),
                        "Quantities": st.session_state.get('pickup_quantities', {}),
                        "Store": store,
                        "Pickup Code": pickup_code
                    })
        if st.button("Start New Order", type="secondary", key="start_new_order_btn"):
            st.session_state['pickup_order_placed'] = False
            st.session_state['pickup_data'] = None
            st.session_state['pickup_cart'] = []
            st.session_state['pickup_quantities'] = {}
            st.session_state['final_cart'] = []
            st.session_state['cart_data'] = None
            st.session_state['show_cart_review'] = False
            st.session_state['cart_processed'] = False
            st.session_state['handled_items'] = set()
            st.session_state['cart_choices'] = {}
            st.session_state['order_id'] = None
            st.rerun()
        st.stop()  # Prevents rest of the tab from running after order is placed

    # --- User Guidance ---
    st.markdown("""
    **Workflow:**
    1. Build and confirm your cart in the Cart tab.
    2. Click 'Get Pickup Suggestion' to find the best store and get a pickup code.
    3. Click 'Place Pickup Order' to finalize your order and get your QR code.
    """)

    # --- Data Checks ---
    if not st.session_state.get('pickup_cart'):
        st.warning("No finalized cart found. Please process your cart and review it first (see Cart tab).")
        st.stop()
    if 'pickup_data' not in st.session_state or not st.session_state['pickup_data']:
        st.info("You need to get a pickup suggestion before placing your order.")
    else:
        data = st.session_state['pickup_data']
        store = data.get('store')
        pickup_code = data.get('pickup_code')
        if not store or not pickup_code:
            st.error("Pickup suggestion is missing store or pickup code. Please try again.")
        else:
            st.markdown("### 🏬 Why this Walmart?\nThis store was selected because it has the most items from your cart in stock and is closest to your location.")
            st.success(f"🏬 Store: {store['name'] if store else 'No store found'}")
            if store and store.get('address'):
                st.markdown(f"**Address:** {store['address']}")
                if store.get('lat') and store.get('lon'):
                    gmap_url = f"https://www.google.com/maps/search/?api=1&query={store['lat']},{store['lon']}"
                    st.markdown(f"[📍 Open in Google Maps]({gmap_url})")
            if store and store.get('lat') and store.get('lon'):
                st.map(data=[{"lat": store['lat'], "lon": store['lon']}], zoom=12)
            st.markdown(f"**Pickup Code:** `{pickup_code}`")

            # --- Show missing items at the store ---
            missing_items = data.get('missing_items', [])
            nearest_stores = data.get('nearest_stores_for_missing', {})
            if missing_items:
                st.warning('Some items are not available at this store:')
                for item in missing_items:
                    name = item.get('name', str(item)) if isinstance(item, dict) else str(item)
                    location = item.get('location') if isinstance(item, dict) else None
                    store_info = nearest_stores.get(name) if isinstance(nearest_stores, dict) else None
                    line = f"- **{name}**"
                    if location:
                        line += f" _(Aisle: {location})_"
                    if store_info:
                        store_name = store_info.get('name', 'Unknown Store')
                        store_addr = store_info.get('address', '')
                        line += f"<br> &nbsp;&nbsp;📍 <b>Available at:</b> {store_name}, {store_addr}"
                    st.markdown(line, unsafe_allow_html=True)

            # --- Place Pickup Order Button ---
            cart = st.session_state.get('pickup_cart', [])
            quantities = st.session_state.get('pickup_quantities', {})
            profile = st.session_state.get('profile_data', {})
            order_payload = {
                "cart": cart,
                "quantities": quantities,
                "store": store,
                "pickup_code": pickup_code,
                "profile": profile
            }
            # st.write("**DEBUG: Order payload to be sent:**", order_payload)
            can_place_order = bool(cart and store and pickup_code)
            if not can_place_order:
                st.error("Cannot place order: missing cart, store, or pickup code. Please follow the workflow above.")
            if st.button("Place Pickup Order", type="primary", key="place_pickup_order_btn", disabled=not can_place_order):
                try:
                    resp = requests.post(f"{API_URL}/place-order", json=order_payload, timeout=30)
                    if resp.status_code == 200 and resp.json().get("success"):
                        st.session_state['pickup_order_placed'] = True
                        st.session_state['order_id'] = resp.json().get('order_id')
                        st.rerun()
                    else:
                        st.error(f"Failed to place order: {resp.json().get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Failed to place order: {e}")

    # --- Pickup Suggestion Button ---
    if st.button("Get Pickup Suggestion", key="pickup_btn"):
        with st.spinner("Finding best store..."):
            try:
                resp = requests.post(f"{API_URL}/pickup-suggestion", json={"cart": st.session_state.pickup_cart})
                if resp.status_code == 200:
                    st.session_state['pickup_data'] = resp.json()
                    st.session_state['pickup_order_placed'] = False  # Reset order placed flag on new suggestion
                    st.rerun()
                else:
                    st.error(f"Failed to get pickup suggestion: {resp.json().get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"Request failed: {e}")