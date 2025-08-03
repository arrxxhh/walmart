import streamlit as st

tab_profile, tab_cart, tab_pickup, tab_scan = st.tabs(["Profile", "Cart", "Pickup", "Scan Product"])

with tab_scan:
    st.write("If you see this, the tab is working.") 