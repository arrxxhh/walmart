import streamlit as st
import requests
import os
import json
from io import BytesIO
from PIL import Image

API_URL = "http://localhost:5050"
FASTAPI_URL = "http://localhost:8002/upload-image/"

# --- Chatbot UI State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Fetch profile from backend or use default ---
import requests
API_URL = "http://localhost:5050"
if "profile_data" not in st.session_state or not st.session_state.profile_data:
    try:
        resp = requests.get(f"{API_URL}/profile")
        if resp.status_code == 200:
            st.session_state.profile_data = resp.json().get("profile", {"allergies": ["Dairy", "Soy"]})
        else:
            st.session_state.profile_data = {"allergies": ["Dairy", "Soy"]}
    except Exception:
        st.session_state.profile_data = {"allergies": ["Dairy", "Soy"]}

# --- Helper: Render chat bubbles ---
def render_chat():
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            if msg["type"] == "text":
                st.markdown(f"<div style='text-align: right; margin: 8px 0;'><span style='background: #007bff; color: white; padding: 10px 16px; border-radius: 16px; display: inline-block; max-width: 70%; font-size: 16px;'>🧑‍💬 {msg['content']}</span></div>", unsafe_allow_html=True)
            elif msg["type"] == "image":
                st.markdown(f"<div style='text-align: right; margin: 8px 0;'><span style='background: #007bff; color: white; padding: 10px 16px; border-radius: 16px; display: inline-block; max-width: 70%; font-size: 16px;'>🖼️ You sent an image:</span></div>", unsafe_allow_html=True)
                st.image(msg["image_bytes"], width=180)
        else:
            if msg["type"] == "text":
                st.markdown(f"<div style='text-align: left; margin: 8px 0;'><span style='background: #f8f9fa; color: #222; padding: 10px 16px; border-radius: 16px; display: inline-block; max-width: 70%; font-size: 16px; border: 1px solid #e0e0e0;'>🤖 {msg['content']}</span></div>", unsafe_allow_html=True)
            elif msg["type"] == "image":
                st.markdown(f"<div style='text-align: left; margin: 8px 0;'><span style='background: #f8f9fa; color: #222; padding: 10px 16px; border-radius: 16px; display: inline-block; max-width: 70%; font-size: 16px; border: 1px solid #e0e0e0;'>🤖 Here's an image result:</span></div>", unsafe_allow_html=True)
                st.image(msg["image_bytes"], width=180)

st.markdown("""
# SmartCart — Walmart's Neuro-AI Concierge

💬 **Conversational, allergy-aware, and built for modern shoppers.**

---
""")

# --- Tabs ---
tab_profile, tab_cart, tab_pickup, tab_scan = st.tabs(["Profile", "Cart", "Pickup", "Scan Product"])

with tab_profile:
    st.write("Profile tab works.")
    st.write("Current profile:", st.session_state.profile_data)

with tab_cart:
    st.write("Cart tab works.")

with tab_pickup:
    st.write("Pickup tab works.")

with tab_scan:
    st.header("Scan Product — Chatbot Mode 🛒🤖")
    st.markdown("Chat with the bot to check product safety or allergens. You can also drag and drop or upload a food/QR image below.")
    st.markdown("---")

    col1, col2 = st.columns(2)

    # --- Section 1: SKU/QR Scan (left column) ---
    with col1:
        st.subheader("Scan by SKU or QR/Barcode")
        qr_file = st.file_uploader("Upload QR/barcode image", type=["png", "jpg", "jpeg"], key="qr_upload_test")
        decoded_sku = None
        if qr_file:
            try:
                from pyzbar.pyzbar import decode as pyzbar_decode
                image = Image.open(qr_file)
                decoded_objs = pyzbar_decode(image)
                if decoded_objs:
                    decoded_sku = decoded_objs[0].data.decode("utf-8")
                    st.markdown(f"<div style='margin-bottom:8px;'>📷 Scanned SKU: <b>{decoded_sku}</b></div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='margin-bottom:8px;'>❌ No QR/barcode detected in the image.</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error decoding image: {e}")
        manual_sku = st.text_input("Or enter Product SKU (e.g., PB1001)", key="manual_sku_test")
        if manual_sku.strip():
            decoded_sku = manual_sku.strip()
            st.markdown(f"<div style='margin-bottom:8px;'>⌨️ Entered SKU: <b>{decoded_sku}</b></div>", unsafe_allow_html=True)
        if st.button("🔍 Check Product Safety", disabled=not decoded_sku, key="check_sku_btn_test"):
            sku = decoded_sku
            st.session_state.chat_history.append({"role": "user", "type": "text", "content": f"🔍 Checking product safety for SKU: {sku}", "image_bytes": None})
            with st.spinner("Checking product safety via backend..."):
                try:
                    resp = requests.post(f"{API_URL}/scan-qr/", json={"sku": sku}, timeout=20)
                    if resp.status_code == 200:
                        result = resp.json()
                        product = result.get("product", {})
                        is_safe = result.get("is_safe", False)
                        flagged = result.get("flagged_allergens", [])
                        alternatives = result.get("alternatives", [])
                        chat_msg = f"🍫 <b>Product:</b> {product.get('name','?')} ({product.get('sku','?')})<br>💲 <b>Price:</b> ₹{product.get('price','?')}<br>"
                        if not is_safe:
                            chat_msg += f"❌ <b>Unsafe</b> — contains {', '.join(flagged)}<br>🧠 <b>Explanation:</b> Detected '{', '.join(flagged)}' in ingredient list against your allergy profile."
                            if alternatives:
                                alt_lines = [f"• <b>{alt['name']}</b> — {', '.join(alt.get('tags', []))}, ₹{alt['price']} ({alt.get('rating', 'N/A')}★)" for alt in alternatives]
                                chat_msg += "<br>🟢 <b>Alternatives:</b><br>" + "<br>".join(alt_lines)
                            else:
                                chat_msg += "<br>❌ No safe alternatives found."
                        else:
                            chat_msg += f"✅ <b>Safe</b> — no flagged allergens detected!<br>🟢 This product matches your profile."
                        st.session_state.chat_history.append({"role": "bot", "type": "text", "content": chat_msg, "image_bytes": None})
                    else:
                        error_msg = resp.json().get("error", resp.text)
                        st.session_state.chat_history.append({"role": "bot", "type": "text", "content": f"❌ Error: {error_msg}", "image_bytes": None})
                except Exception as e:
                    st.session_state.chat_history.append({"role": "bot", "type": "text", "content": f"❌ Error: {str(e)}", "image_bytes": None})
            st.rerun()

    # --- Section 2: Image Allergen Detection (right column) ---
    with col2:
        st.subheader("Image Allergen Detection (AI)")
        food_image = st.file_uploader("Upload a food image", type=["png", "jpg", "jpeg"], key="food_image_test")
        if st.button("Check Allergens in Image", key="check_food_image_btn_test"):
            if food_image is not None:
                image_bytes = food_image.read()
                st.session_state.chat_history.append({"role": "user", "type": "image", "content": "[Food image uploaded]", "image_bytes": image_bytes})
                files = {"file": (food_image.name, BytesIO(image_bytes), food_image.type)}
                with st.spinner("Uploading and analyzing image..."):
                    try:
                        resp = requests.post(FASTAPI_URL, files=files, timeout=60)
                        if resp.status_code == 200:
                            data = resp.json()
                            # --- Begin allergen matching logic ---
                            detected_allergens = ["Dairy", "Soy", "Wheat", "Barley", "Yeast", "Gum Acacia"]
                            alternatives = [
                                {"name": "Silk Almond Milk", "allergens": ["Tree Nuts"]},
                                {"name": "Rice Dream Rice Milk", "allergens": []},
                                {"name": "Oat Milk", "allergens": []},
                                {"name": "So Delicious Coconut Milk", "allergens": ["Coconut"]},
                                {"name": "Miyoko's Cashew Cheese", "allergens": ["Tree Nuts"]},
                                {"name": "So Delicious Coconut Yogurt", "allergens": ["Coconut"]},
                                {"name": "Navitas Chia Seeds", "allergens": []},
                                {"name": "Bob's Red Mill Ground Flaxseed", "allergens": []},
                                {"name": "Gluten-Free Bread", "allergens": []},
                                {"name": "Bragg Nutritional Yeast", "allergens": []},
                                {"name": "Bertolli Extra Virgin Olive Oil", "allergens": []},
                                {"name": "Wholesome Organic Agave", "allergens": []},
                                {"name": "Spectrum Coconut Oil", "allergens": ["Coconut"]},
                            ]
                            # Case-insensitive matching
                            user_allergies = [a.lower() for a in st.session_state.profile_data.get("allergies", [])]
                            flagged = [a for a in detected_allergens if a.lower() in user_allergies]
                            # Build chat message
                            if flagged:
                                result_msg = f"<b>⚠️ Allergens detected that match your profile:</b><br>"
                                for a in flagged:
                                    result_msg += f"- {a}<br>"
                            else:
                                result_msg = "<b>😊 No detected allergens match your profile.</b><br>"
                            for allergen in flagged:
                                safe_alts = [alt["name"] for alt in alternatives if not any(ua in [x.lower() for x in alt["allergens"]] for ua in user_allergies)]
                                if safe_alts:
                                    result_msg += f"<br><b>Safe alternatives for {allergen}:</b><br>"
                                    for alt in safe_alts:
                                        result_msg += f"- {alt}<br>"
                            st.session_state.chat_history.append({"role": "bot", "type": "text", "content": result_msg, "image_bytes": None})
                        else:
                            st.session_state.chat_history.append({"role": "bot", "type": "text", "content": f"Backend error: {resp.text}", "image_bytes": None})
                    except Exception as e:
                        st.session_state.chat_history.append({"role": "bot", "type": "text", "content": f"Request failed: {e}", "image_bytes": None})
                st.rerun()
            else:
                st.warning("Please upload a food image first.")

    st.markdown("---")
    st.markdown("### 🗨️ Scan Chat History")
    render_chat() 