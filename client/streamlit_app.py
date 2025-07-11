# client/app.py

import streamlit as st
import requests

st.set_page_config(page_title="Walmart Meal Planner", page_icon="🛒")

st.title("🧠 Walmart AI Meal Planner")
st.markdown("Plan smart meals using AI + Walmart-style inventory.")

# --- User Inputs ---
st.sidebar.header("Meal Preferences")

diet = st.sidebar.selectbox("Diet Type", ["vegetarian", "non-vegetarian", "vegan"])
servings = st.sidebar.slider("Servings", 1, 10, 2)
budget = st.sidebar.number_input("Budget (₹)", min_value=50, max_value=1000, value=300, step=10)
restrictions = st.sidebar.text_input("Allergies / Avoid items", "milk, peanuts")
time_limit = st.sidebar.selectbox("Time Limit", ["15 mins", "30 mins", "45 mins", "1 hour", "2 hours"])

if st.sidebar.button("Generate Meal Plan 🍽️"):
    with st.spinner("Generating meal..."):
        try:
            # API Request
            resp = requests.post("http://localhost:5000/generate-meal", json={
                "diet": diet,
                "servings": servings,
                "budget": budget,
                "restrictions": restrictions,
                "time_limit": time_limit
            })

            if resp.status_code == 200:
                data = resp.json()

                st.success(f"🍲 **{data['meal_name']}**")

                st.subheader("🧾 Ingredients")
                for i in data["ingredients"]:
                    st.write(f"- {i['quantity']} {i['name']}")

                st.subheader("📋 Instructions")
                for idx, step in enumerate(data["instructions"], 1):
                    st.markdown(f"{idx}. {step}")

                st.subheader("🛍️ Walmart Cart")
                total = 0
                for c in data["cart"]:
                    st.write(f"₹{c['price']} - {c['name']}")
                    total += c['price']

                st.markdown("---")
                st.subheader("💰 Budget Summary")
                st.write(f"**Your Budget:** ₹{budget}")
                st.write(f"**Total Meal Cost:** ₹{data['total']}")

                if data['total'] <= budget:
                    st.success("✅ You're within budget!")
                else:
                    st.error("❌ Over budget! Try increasing budget or limiting ingredients.")
            else:
                st.error(f"Server error: {resp.json().get('error')}")
        except Exception as e:
            st.error(f"Request failed: {str(e)}")
