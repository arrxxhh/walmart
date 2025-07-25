# Walmart Allergen Detection System

A FastAPI-based AI system that detects allergens in food images and suggests safe alternatives using Google's Gemini AI and Pinecone vector database.

## Features

- **Image Upload & Processing**: Accepts food images via HTTP POST requests
- **AI-Powered Allergen Detection**: Uses Google's Gemini 2.0 Flash model to identify allergens in images
- **Alternative Product Suggestions**: Uses Pinecone vector database to find allergen-free alternatives
- **Two-Stage AI Processing**: First identifies allergens, then provides comprehensive analysis with alternatives

## Setup Instructions

### 1. Environment Variables

Create a `.env` file in the dhruvi directory with the following variables:

```env
# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=gcp-starter

# Google Generative AI Configuration
GOOGLE_API_KEY=your_google_api_key_here
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be accessible at `http://localhost:8000`

## API Endpoints

### POST `/upload-image/`
Upload and process food images for allergen detection.

**Request**: Multipart form with image file
**Response**: JSON with allergen analysis and alternative suggestions

### GET `/get-allergens/`
Retrieve the latest allergen detection result.

**Response**: JSON with the most recent allergen analysis

## Integration with Main Walmart System

This allergen detection system can be integrated into the main Walmart SmartCart application by:

1. **Adding an image upload feature** to the Streamlit frontend
2. **Calling the allergen detection API** when users upload food images
3. **Displaying allergen warnings** and alternative suggestions in the cart
4. **Filtering products** based on detected allergens

## Dependencies

- FastAPI for the web framework
- Google Generative AI (Gemini) for image analysis
- Pinecone for vector similarity search
- Pillow for image processing
- httpx for HTTP requests
- Streamlit for frontend integration
- Flask for backend integration

## Files

- `main.py` - FastAPI application with allergen detection logic
- `items.json` - Product database with allergen information
- `requirements.txt` - Python dependencies
- `README.md` - This file
