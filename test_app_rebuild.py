import streamlit as st
import requests
import os
import json

API_URL = "http://localhost:5050"

tab_profile, tab_cart, tab_pickup, tab_scan = st.tabs(["Profile", "Cart", "Pickup", "Scan Product"])

with tab_profile:
    st.markdown("### 🔹 Section 1: Personalizing Your SmartCart 🧠")
    st.write(
        """
Let’s begin by understanding your needs, your household, and what matters most when you shop.

This GenAI assistant will convert your description into a personalized customer profile — detecting allergies, dietary preferences, budget goals, and more.
"""
    )
    # --- Robust Profile Loading at Startup ---
    if "profile_data" not in st.session_state or st.session_state.profile_data is None:
        try:
            resp = requests.get(f"{API_URL}/profile")
            if resp.status_code == 200:
                st.session_state.profile_data = resp.json().get("profile")
        except Exception:
            st.session_state.profile_data = None

    if st.session_state.profile_data:
        st.success("A customer profile is active. You can now provide updates.")
        st.subheader("Current Customer Profile")
        st.json(st.session_state.profile_data)
    else:
        st.warning("No profile found. Please create one in the Profile tab of your main app.")

with tab_cart:
    st.write("Cart tab works.")

with tab_pickup:
    st.write("Pickup tab works.")

with tab_scan:
    st.write("Scan Product tab works.")