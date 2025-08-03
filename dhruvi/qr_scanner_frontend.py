# Feature 5: In-Store QR/Barcode Scanner for Allergen Checks & Alternatives
import streamlit as st
import requests
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode
import json
import time

API_BASE_URL = "http://localhost:8001"

st.set_page_config(
    page_title="Walmart SmartCart - Product Scanner",
    page_icon="📱",
    layout="centered"
)

# Initialize session state for chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_user" not in st.session_state:
    st.session_state.current_user = "user_001"

def add_chat_message(message, is_user=False, message_type="text"):
    """Add message to chat history"""
    st.session_state.chat_history.append({
        "message": message,
        "is_user": is_user,
        "type": message_type,
        "timestamp": time.time()
    })

def display_chat_history():
    """Display chat history with proper styling"""
    for msg in st.session_state.chat_history:
        if msg["is_user"]:
            st.markdown(f"""
            <div style="text-align: right; margin: 10px 0;">
                <div style="background-color: #007bff; color: white; padding: 10px; border-radius: 15px; display: inline-block; max-width: 70%;">
                    {msg["message"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="text-align: left; margin: 10px 0;">
                <div style="background-color: #f8f9fa; color: black; padding: 10px; border-radius: 15px; display: inline-block; max-width: 70%; border: 1px solid #dee2e6;">
                    {msg["message"]}
                </div>
            </div>
            """, unsafe_allow_html=True)

# Main UI
st.title("🛒 Walmart SmartCart - Product Scanner")
st.markdown("**Scan any product to check if it's safe for your dietary needs!**")

# User Profile Selection
col1, col2 = st.columns([2, 1])
with col1:
    user_options = {
        "user_001": "John Doe (Peanut Allergy, Low Fat)",
        "user_002": "Jane Smith (Dairy Allergy, Vegan)"
    }
    selected_user = st.selectbox(
        "Select your profile:",
        options=list(user_options.keys()),
        format_func=lambda x: user_options[x],
        index=0 if st.session_state.current_user == "user_001" else 1
    )
    
    if selected_user != st.session_state.current_user:
        st.session_state.current_user = selected_user
        st.session_state.chat_history = []  # Clear chat for new user
        add_chat_message("👋 Welcome! I'm your personal shopping assistant. I'll help you find safe products that match your dietary needs.", is_user=False)

with col2:
    if st.button("🔄 Reset Chat"):
        st.session_state.chat_history = []
        add_chat_message("👋 Welcome! I'm your personal shopping assistant. I'll help you find safe products that match your dietary needs.", is_user=False)
        st.rerun()

# Display current user profile
@st.cache_data(show_spinner=False)
def get_user_profile(user_id):
    try:
        r = requests.get(f"{API_BASE_URL}/user-profile/{user_id}")
        if r.status_code == 200:
            return r.json()["user_profile"]
    except Exception:
        pass
    return None

profile = get_user_profile(st.session_state.current_user)
if profile:
    st.info(f"**Your Profile:** Allergies: {', '.join(profile.get('allergies', []))} | Preferences: {', '.join(profile.get('dietary_preferences', []))}")

# Chat Interface
st.markdown("---")
st.subheader("💬 Product Safety Chat")

# Display chat history
display_chat_history()

# Scan Product Section
st.markdown("---")
st.subheader("📱 Scan Product")

# Input methods
tab1, tab2 = st.tabs(["📷 Upload QR/Barcode", "⌨️ Enter SKU Manually"])

with tab1:
    uploaded_file = st.file_uploader(
        "Upload a product QR or barcode image",
        type=["png", "jpg", "jpeg"],
        help="Take a photo of the product's QR code or barcode"
    )
    
    decoded_sku = None
    if uploaded_file:
        try:
            image = Image.open(uploaded_file)
            decoded_objs = pyzbar_decode(image)
            if decoded_objs:
                decoded_sku = decoded_objs[0].data.decode("utf-8")
                st.success(f"✅ Detected SKU: **{decoded_sku}**")
                add_chat_message(f"📷 I scanned a product with SKU: {decoded_sku}", is_user=True)
            else:
                st.warning("❌ No QR/barcode detected in the image. Please try again.")
        except Exception as e:
            st.error(f"❌ Error decoding image: {e}")

with tab2:
    manual_sku = st.text_input(
        "Enter Product SKU",
        placeholder="e.g., WALMART_001, PB1001",
        help="Enter the product's SKU or barcode number"
    )
    if manual_sku.strip():
        decoded_sku = manual_sku.strip()
        add_chat_message(f"⌨️ I entered SKU: {decoded_sku}", is_user=True)

# Scan Button
sku_to_check = decoded_sku
if st.button("🔍 Scan Product & Check Safety", disabled=not sku_to_check, type="primary"):
    if sku_to_check:
        with st.spinner("🔍 Scanning product and checking safety..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/scan-qr/",
                    json={"qr_code_data": sku_to_check, "user_id": st.session_state.current_user},
                    timeout=20
                )
                
                if response.status_code == 200:
                    result = response.json()
                    product = result["product"]
                    safety = result["safety_analysis"]
                    
                    # Build chatbot response
                    chat_response = f"""🍫 **Product:** {product['name']} ({product['id']})
💰 **Price:** ${product['price']:.2f}
🏷️ **Brand:** {product['brand']}"""

                    if not safety["is_safe"]:
                        chat_response += f"""
❌ **Unsafe** — contains {', '.join(product['allergens'])}
🧠 **Explanation:** Detected '{', '.join(product['allergens'])}' in ingredient list against your allergy profile.
⚠️ **Safety Score:** {safety['safety_score']:.0f}/100"""
                        
                        # Add alternatives
                        if result["alternatives"]:
                            chat_response += "\n🟢 **Alternatives:**"
                            for i, alt in enumerate(result["alternatives"][:2], 1):
                                chat_response += f"""
  • {alt['name']} — nut-free, vegan, ${alt['price']:.2f} ({alt['safety_score']:.0f}★)"""
                        else:
                            chat_response += "\n❌ No safe alternatives found in our database."
                    else:
                        chat_response += f"""
✅ **Safe** — no flagged allergens detected!
🟢 **Safety Score:** {safety['safety_score']:.0f}/100
🥗 **Nutrition:** {product['nutrition']['calories']} cal, {product['nutrition']['total_fat']}g fat"""
                    
                    add_chat_message(chat_response, is_user=False)
                    st.rerun()
                    
                else:
                    error_msg = f"❌ Product not found or error: {response.text}"
                    add_chat_message(error_msg, is_user=False)
                    st.rerun()
                    
            except Exception as e:
                error_msg = f"❌ Error scanning product: {str(e)}"
                add_chat_message(error_msg, is_user=False)
                st.rerun()

# Quick Test Buttons
st.markdown("---")
st.subheader("🧪 Quick Test Products")

col1, col2, col3 = st.columns(3)
test_products = [
    ("WALMART_001", "Peanut Butter", "❌ Unsafe for peanut allergy"),
    ("WALMART_002", "SunButter", "✅ Safe alternative"),
    ("WALMART_003", "Almond Milk", "⚠️ Tree nut allergy"),
    ("WALMART_004", "Butter", "❌ Dairy allergy"),
    ("WALMART_005", "Vegan Spread", "✅ Safe for vegans")
]

for i, (sku, name, status) in enumerate(test_products):
    col = [col1, col2, col3][i % 3]
    with col:
        if st.button(f"Test {name}", key=f"test_{sku}"):
            add_chat_message(f"🧪 Testing: {name} ({sku})", is_user=True)
            st.session_state.test_sku = sku
            st.rerun()

# Handle test button clicks
if hasattr(st.session_state, 'test_sku'):
    sku = st.session_state.test_sku
    del st.session_state.test_sku
    
    with st.spinner("🔍 Testing product..."):
        try:
            response = requests.post(
                f"{API_BASE_URL}/scan-qr/",
                json={"qr_code_data": sku, "user_id": st.session_state.current_user},
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                product = result["product"]
                safety = result["safety_analysis"]
                
                chat_response = f"""🍫 **Product:** {product['name']} ({product['id']})
💰 **Price:** ${product['price']:.2f}"""

                if not safety["is_safe"]:
                    chat_response += f"""
❌ **Unsafe** — contains {', '.join(product['allergens'])}
🧠 **Explanation:** Detected '{', '.join(product['allergens'])}' in ingredient list against your allergy profile."""
                    
                    if result["alternatives"]:
                        chat_response += "\n🟢 **Alternatives:**"
                        for alt in result["alternatives"][:2]:
                            chat_response += f"""
  • {alt['name']} — nut-free, vegan, ${alt['price']:.2f} ({alt['safety_score']:.0f}★)"""
                else:
                    chat_response += f"""
✅ **Safe** — no flagged allergens detected!"""
                
                add_chat_message(chat_response, is_user=False)
                st.rerun()
                
        except Exception as e:
            add_chat_message(f"❌ Error: {str(e)}", is_user=False)
            st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
    <p>🔍 <strong>How it works:</strong> Scan any product QR/barcode to instantly check safety against your profile!</p>
    <p>🚨 <strong>Allergies:</strong> Automatically detects and warns about allergens</p>
    <p>🥗 <strong>Preferences:</strong> Checks against your dietary preferences</p>
    <p>🔄 <strong>Alternatives:</strong> Suggests safe, in-stock alternatives</p>
</div>
""", unsafe_allow_html=True) 