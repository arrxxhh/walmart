"""
Integration Example: How to use the Allergen Detection API with the main Walmart system
"""

import requests
import json
from typing import Dict, List, Optional

class AllergenDetectionClient:
    """Client for interacting with the Allergen Detection API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def upload_image_for_allergen_detection(self, image_path: str) -> Dict:
        """
        Upload an image to detect allergens and get alternative suggestions
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict containing allergen analysis and alternative suggestions
        """
        try:
            with open(image_path, 'rb') as image_file:
                files = {'file': image_file}
                response = requests.post(
                    f"{self.base_url}/upload-image/",
                    files=files,
                    timeout=120  # Longer timeout for AI processing
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"error": f"Failed to upload image: {str(e)}"}
    
    def get_latest_allergen_result(self) -> Dict:
        """
        Get the latest allergen detection result
        
        Returns:
            Dict containing the most recent allergen analysis
        """
        try:
            response = requests.get(f"{self.base_url}/get-allergens/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Failed to get allergen result: {str(e)}"}

# Example usage in Streamlit app
def integrate_with_streamlit():
    """
    Example of how to integrate allergen detection into the Streamlit frontend
    """
    import streamlit as st
    
    # Initialize the client
    allergen_client = AllergenDetectionClient()
    
    st.header("🍽️ Food Allergen Detection")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload a food image to check for allergens",
        type=['jpg', 'jpeg', 'png'],
        help="Upload an image of food to detect potential allergens"
    )
    
    if uploaded_file is not None:
        # Display the uploaded image
        st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
        
        if st.button("🔍 Detect Allergens"):
            with st.spinner("Analyzing image for allergens..."):
                # Save uploaded file temporarily
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                try:
                    # Call the allergen detection API
                    result = allergen_client.upload_image_for_allergen_detection(tmp_path)
                    
                    if "error" not in result:
                        st.success("✅ Allergen analysis complete!")
                        
                        # Display results
                        st.subheader("🔍 Allergen Analysis")
                        st.write(result.get("allergens_and_alternatives", "No analysis available"))
                        
                        # You could also parse the result and show it in a more structured way
                        st.subheader("📋 Summary")
                        st.info("Check the detailed analysis above for allergen information and alternative suggestions.")
                    else:
                        st.error(f"❌ Error: {result['error']}")
                        
                finally:
                    # Clean up temporary file
                    os.unlink(tmp_path)

# Example usage in Flask backend
def integrate_with_flask():
    """
    Example of how to integrate allergen detection into the Flask backend
    """
    from flask import Flask, request, jsonify
    
    app = Flask(__name__)
    allergen_client = AllergenDetectionClient()
    
    @app.route('/check-allergens', methods=['POST'])
    def check_allergens():
        """Endpoint to check allergens in uploaded images"""
        try:
            if 'image' not in request.files:
                return jsonify({"error": "No image file provided"}), 400
            
            file = request.files['image']
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400
            
            # Save file temporarily
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                file.save(tmp_file.name)
                tmp_path = tmp_file.name
            
            try:
                # Call allergen detection API
                result = allergen_client.upload_image_for_allergen_detection(tmp_path)
                return jsonify(result)
            finally:
                # Clean up
                os.unlink(tmp_path)
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    return app

# Example of how to use the client directly
if __name__ == "__main__":
    # Example usage
    client = AllergenDetectionClient()
    
    # Example 1: Upload an image
    # result = client.upload_image_for_allergen_detection("path/to/food_image.jpg")
    # print("Allergen Detection Result:", json.dumps(result, indent=2))
    
    # Example 2: Get latest result
    # latest_result = client.get_latest_allergen_result()
    # print("Latest Result:", json.dumps(latest_result, indent=2))
    
    print("Allergen Detection Client ready for integration!")
    print("Use this client in your Streamlit or Flask applications.") 