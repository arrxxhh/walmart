Walmart Sparkathon Submission 2025,

Pain Points:

Inconsistent availability of shopping lists across stores

Information overload on product details, allergens, and substitutes

Wasted time during in-store navigation and checkout queues

No unified experience between online and in-store Walmart shopping

Problem Chosen Summary:
A wide range of customers, including those with hectic schedules, dietary requirements, and accessibility requirements, are served by retailers such as Walmart. However, out-of-stock items (which 30% of global online grocery shoppers encounter), ambiguous allergen labeling (which 1 in 5 food-allergic consumers worldwide report), ineffective store navigation, and lengthy checkout lines continue to cause major friction for many shoppers. Customers frequently voice their frustration with these problems in reviews, forums, and help channels.

The average visit to a large-format retail store lasts between 40-50 minutes (Statista, 2024), which presents additional difficulties for people with limited time or mobility. There is currently no intelligent co-shopper or AI assistant to streamline the process, from home planning to in-store navigation and pickup coordination, even though multinational retail chains run thousands of locations and serve hundreds of millions of customers every week.

By tackling these issues, there is a significant chance to improve customer satisfaction among a worldwide clientele, expedite the shopping experience, shorten travel times, and encourage inclusivity.



Solution:
How We're Addressing These Issues 
1. Establishing a Conversational Profile Issue: There is no guided setup for customers with specific dietary and lifestyle requirements. Solution: We use natural language (e.g., “I’m vegan and allergic to peanuts”) to gather user preferences using GenAI. It produces structured JSON data from the user's profile, including diet, allergies, and tags. Technology: Gemini 1.5 or GPT-4o, Streamlit chat UI, Python backend.
2. The Smart Substitution Engine Issue: 
Items that are out of stock cause annoyance and manual re-searching. Solution: Uses vector embeddings + filtering (e.g. price, allergens) to recommend safe, reasonably priced, and highly rated alternatives. GenAI provides a clear justification for the switch. Technology: backend logic, GPT-4o, cosine similarity, and OpenAI embeddings. 
 3. Allergen & Ingredient Parser Flagging Issue: Labels with unclear or obscured allergen information. Users can scan or upload ingredient lists as a solution. Allergens and possible hazards are instantly identified by our NLP + rule-based matcher. Tech: local backend logic, fuzzy matching, and regex.
4. AI-Powered Meal Planning Issue: 
Users find it difficult to prepare economical, well-balanced meals using the ingredients at hand. Solution: GenAI creates recipes and meal plans based on store inventory, diet, and budget (e.g., "Dinner for 4 under ₹250, no dairy or nuts") and provides ingredient lists that are ready for carts.

Tech: Prompt-tuned GPT-4o, Streamlit UI, inventory mapping.

5.  Accessibility first design:
A lot of users struggle because of screen fatigue, motor impairments, or low vision. Solution: We provide keyboard/screen reader support, a high contrast user interface, and larger fonts. Everything about the experience is responsive and inclusive. Tech: WCAG standards, simplified accessibility customization.
6. Loyalty Optimizer: 
Users lose out on chances to maximize their spending or receive rewards. Solution: To help users get the most out of their cart, it suggests better-value items based on loyalty multipliers (e.g., "Buy 2, get bonus points"). Tech: Backend item comparison logic and rule-based scoring. 
 7. Pickup Orders Optimizer:
Time and fuel are wasted due to lengthy wait times and ineffective store selection. Solution: Determines pickup ETAs for optimal fulfillment and compares user shopping lists with local store inventories. Technology: backend rule engine, inventory scoring, and geomatching.

Future Scope
 •  Voice-Based Search & Commands: Will allow users to speak queries like “Find gluten-free snacks under ₹150,” parsed into filters using speech-to-text + NLP.
 • Mobile App Integration: Extend functionality to Android/iOS via Streamlit export or frontend wrappers.
 •        Feedback-Based Personalization: Fine-tune substitutions using user sentiment (e.g., “too sweet” or “liked this brand”).
