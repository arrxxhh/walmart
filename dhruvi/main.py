# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import base64
import httpx
import os
import io
import json
from PIL import Image
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Initialize the FastAPI app
app = FastAPI(
    title="Allergen Detector API",
    description="A FastAPI server to detect potential allergens in food images using an LLM."
)

# In-memory storage for the latest LLM response.
# In a production environment, this would typically be stored in a database (e.g., PostgreSQL, MongoDB)
# or a caching system (e.g., Redis) for persistence and scalability.
latest_llm_response: str = "No image processed yet. Please upload an image first."

# Pinecone and Google Generative AI setup
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT") # e.g., "gcp-starter" or "us-west-2"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # Fallback to hardcoded if not in env

if not PINECONE_API_KEY or not PINECONE_ENVIRONMENT:
    raise ValueError("Pinecone API key and environment must be set in .env file")
if not GOOGLE_API_KEY:
    raise ValueError("Google API key must be set in .env file or provided in code")

# Initialize Pinecone
pinecone_client = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
INDEX_NAME = "allergen-alternatives"

# Initialize Google Generative AI for embeddings
genai.configure(api_key=GOOGLE_API_KEY)
embedding_model = "models/embedding-001"

# Function to generate embeddings
async def generate_embedding(text: str):
    response = genai.embed_content(model=embedding_model, content=text)
    return response["embedding"]

# Function to load items and upsert to Pinecone
async def load_and_embed_items():
    try:
        with open("items.json", "r") as f:
            items = json.load(f)

        # Check if index exists, create if not
        if INDEX_NAME not in pinecone_client.list_indexes():
            try:
                pinecone_client.create_index(
                    name=INDEX_NAME,
                    dimension=768, # Dimension for Google's embedding-001 model
                    metric="cosine",
                    spec=ServerlessSpec(cloud='aws', region='us-east-1') # Specify the index type and cloud provider
                )
                print(f"Pinecone index '{INDEX_NAME}' created.")
            except Exception as e:
                # Check if the error is due to the index already existing
                if "409" in str(e) and "ALREADY_EXISTS" in str(e):
                    print(f"Pinecone index '{INDEX_NAME}' already exists. Connecting to existing index.")
                else:
                    raise e # Re-raise other exceptions
        
        # Get the index instance after ensuring it exists
        index = pinecone_client.Index(INDEX_NAME)

        vectors_to_upsert = []
        for item in items:
            # Create a combined text for embedding
            text_to_embed = f"Name: {item['name']}. Description: {item['description']}. Allergens: {', '.join(item['allergens'])}. Availability: {item['availability']}."
            embedding = await generate_embedding(text_to_embed)
            vectors_to_upsert.append({
                "id": item["id"],
                "values": embedding,
                "metadata": item # Store full item data as metadata
            })
        
        if vectors_to_upsert:
            index.upsert(vectors=vectors_to_upsert)
            print(f"Upserted {len(vectors_to_upsert)} items to Pinecone.")
        else:
            print("No items to upsert.")

    except Exception as e:
        print(f"Error loading or embedding items: {e}")

# Run this on startup
@app.on_event("startup")
async def startup_event():
    await load_and_embed_items()

# Define the request body for the LLM API call
class LLMPayload(BaseModel):
    contents: list

# Define the response structure for the LLM API call
class LLMResponse(BaseModel):
    candidates: list

@app.post("/upload-image/", summary="Upload an image to detect allergens")
async def upload_image(file: UploadFile = File(...)):
    """
    Receives an image from the frontend, sends it to an LLM for allergen detection,
    and stores the LLM's response.
    """
    global latest_llm_response

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    try:
        # Read the image content
        image_data = await file.read()

        # Optional: Validate image using Pillow to ensure it's a valid image
        try:
            Image.open(io.BytesIO(image_data))
        except IOError:
            raise HTTPException(status_code=400, detail="Could not process image file. It might be corrupted.")

        # Encode image to base64
        base64_image = base64.b64encode(image_data).decode("utf-8")

        # Define the initial prompt for the LLM to identify allergens
        initial_prompt_text = "List out the potential allergens in the food shown in this image. Be concise and list them clearly, separated by commas. For example: 'gluten, dairy, nuts'."

        # Construct the payload for the initial LLM API call
        initial_llm_payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": initial_prompt_text},
                        {
                            "inlineData": {
                                "mimeType": file.content_type,
                                "data": base64_image
                            }   
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "topK": 32,
                "topP": 1,
                "maxOutputTokens": 2048,
                "stopSequences": []
            }
        }

        # LLM API configuration
        api_key = GOOGLE_API_KEY
        llm_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

        # Make the initial API call to the LLM
        async with httpx.AsyncClient() as client:
            initial_llm_response = await client.post(llm_api_url, json=initial_llm_payload, timeout=60.0)
            initial_llm_response.raise_for_status()
            initial_response_data = initial_llm_response.json()

        # Extract allergens from the initial LLM response
        allergens_text = ""
        if initial_response_data and initial_response_data.get("candidates"):
            first_candidate = initial_response_data["candidates"][0]
            if first_candidate.get("content") and first_candidate["content"].get("parts"):
                allergens_text = first_candidate["content"]["parts"][0].get("text", "")
            else:
                raise HTTPException(status_code=500, detail="LLM response structure unexpected: missing content or parts in initial response.")
        else:
            raise HTTPException(status_code=500, detail="LLM response structure unexpected: missing candidates in initial response.")

        # Parse allergens (simple comma-separated split)
        identified_allergens = [a.strip().lower() for a in allergens_text.split(',') if a.strip()]
        
        alternatives_info = []
        if identified_allergens:
            # Get the index instance inside the function where it's used
            index = pinecone_client.Index(INDEX_NAME)
            for allergen in identified_allergens:
                # Generate embedding for the allergen to search for alternatives
                allergen_embedding = await generate_embedding(f"alternative to {allergen}")
                
                # Perform similarity search in Pinecone for in-stock items
                query_results = index.query(
                    vector=allergen_embedding,
                    top_k=5, # Get top 5 similar items
                    filter={
                        "availability": {"$eq": "in_stock"},
                        "allergens": {"$nin": [allergen]} # Exclude items that contain the allergen itself
                    },
                    include_metadata=True
                )
                
                found_alternatives = []
                for match in query_results.matches:
                    item_name = match.metadata.get("name")
                    item_description = match.metadata.get("description")
                    item_allergens = match.metadata.get("allergens")
                    if item_name:
                        found_alternatives.append(f"- {item_name} ({item_description}). Contains: {', '.join(item_allergens) if item_allergens else 'none'}.")
                
                if found_alternatives:
                    alternatives_info.append(f"For '{allergen}' (identified as an allergen), consider these in-stock alternatives:\n" + "\n".join(found_alternatives))
                else:
                    alternatives_info.append(f"No in-stock alternatives found for '{allergen}'.")
        else:
            alternatives_info.append("No specific allergens identified by the LLM in the image.")

        # Construct the final prompt for the LLM with alternatives
        final_prompt_text = (
            f"Based on the image, the identified allergens are: {allergens_text}.\n\n"
            f"Here is information about potential in-stock alternatives from our store:\n"
            f"{' '.join(alternatives_info)}\n\n"
            f"Please provide a comprehensive response that lists the potential allergens in the food shown in the image, "
            f"and for each allergen, suggest alternative ingredients or products from the provided in-stock list. "
            f"If no suitable in-stock alternative is found, suggest a general alternative. "
            f"Be clear, concise, and helpful."
        )

        # Construct the payload for the final LLM API call
        final_llm_payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": final_prompt_text},
                        {
                            "inlineData": {
                                "mimeType": file.content_type,
                                "data": base64_image
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "topK": 32,
                "topP": 1,
                "maxOutputTokens": 2048,
                "stopSequences": []
            }
        }

        # Make the final API call to the LLM
        async with httpx.AsyncClient() as client:
            final_llm_response = await client.post(llm_api_url, json=final_llm_payload, timeout=60.0)
            final_llm_response.raise_for_status()
            final_response_data = final_llm_response.json()

        # Extract the text from the final LLM response
        if final_response_data and final_response_data.get("candidates"):
            final_candidate = final_response_data["candidates"][0]
            if final_candidate.get("content") and final_candidate["content"].get("parts"):
                llm_generated_text = final_candidate["content"]["parts"][0].get("text", "No text content found in LLM response.")
                latest_llm_response = llm_generated_text
            else:
                latest_llm_response = "LLM response structure unexpected: missing content or parts in final response."
        else:
            latest_llm_response = "LLM response structure unexpected: missing candidates in final response."

        return JSONResponse(
            status_code=200,
            content={"message": "Image uploaded and processed successfully!", "allergens_and_alternatives": latest_llm_response}
        )

    except httpx.HTTPStatusError as e:
        # Handle HTTP errors from the LLM API
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error from LLM API: {e.response.text}"
        )
    except httpx.RequestError as e:
        # Handle network errors or other request issues
        raise HTTPException(
            status_code=500,
            detail=f"Network error when calling LLM API: {e}"
        )
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")

@app.get("/get-allergens/", summary="Retrieve the latest allergen detection result")
async def get_allergens():
    """
    Returns the latest allergen detection result generated by the LLM.
    """
    global latest_llm_response
    return JSONResponse(
        status_code=200,
        content={"allergens_and_alternatives": latest_llm_response}
    )

# To run this server:
# 1. Save the code as `main.py`
# 2. Install dependencies: `pip install fastapi uvicorn python-multipart Pillow httpx`
# 3. Run the server: `uvicorn main:app --reload`
# The API will be accessible at http://127.0.0.0:8000
