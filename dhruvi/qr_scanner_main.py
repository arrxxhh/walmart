# QR Code Scanner for Allergen Detection
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import qrcode
import json
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
import requests
import re

# Load environment variables
load_dotenv()

# Initialize the FastAPI app
app = FastAPI(
    title="Walmart QR Scanner - Allergen & Preference Checker",
    description="QR code scanner that checks products against user preferences and suggests alternatives"
)

# Sample product database (in real implementation, this would come from Walmart's API)
PRODUCTS_DATABASE = {
    "WALMART_001": {
        "id": "WALMART_001",
        "name": "Jif Creamy Peanut Butter",
        "brand": "Jif",
        "category": "Pantry",
        "ingredients": ["peanuts", "sugar", "molasses", "fully hydrogenated vegetable oils", "salt"],
        "nutrition": {
            "calories": 190,
            "total_fat": 16,
            "saturated_fat": 3,
            "protein": 7,
            "carbs": 7
        },
        "allergens": ["peanuts"],
        "dietary_flags": ["high_fat", "high_calories"],
        "price": 3.99,
        "image_url": "https://example.com/jif-peanut-butter.jpg"
    },
    "WALMART_002": {
        "id": "WALMART_002", 
        "name": "SunButter Sunflower Seed Butter",
        "brand": "SunButter",
        "category": "Pantry",
        "ingredients": ["sunflower seeds", "sugar", "salt", "natural flavor"],
        "nutrition": {
            "calories": 200,
            "total_fat": 18,
            "saturated_fat": 2,
            "protein": 7,
            "carbs": 6
        },
        "allergens": [],
        "dietary_flags": ["high_fat"],
        "price": 4.99,
        "image_url": "https://example.com/sunbutter.jpg"
    },
    "WALMART_003": {
        "id": "WALMART_003",
        "name": "Silk Almond Milk Unsweetened",
        "brand": "Silk",
        "category": "Dairy",
        "ingredients": ["almond milk", "vitamin e", "calcium carbonate", "vitamin d2"],
        "nutrition": {
            "calories": 30,
            "total_fat": 2.5,
            "saturated_fat": 0,
            "protein": 1,
            "carbs": 1
        },
        "allergens": ["tree_nuts"],
        "dietary_flags": ["low_fat", "low_calories"],
        "price": 3.49,
        "image_url": "https://example.com/silk-almond.jpg"
    },
    "WALMART_004": {
        "id": "WALMART_004",
        "name": "Land O'Lakes Butter",
        "brand": "Land O'Lakes", 
        "category": "Dairy",
        "ingredients": ["cream", "salt"],
        "nutrition": {
            "calories": 100,
            "total_fat": 11,
            "saturated_fat": 7,
            "protein": 0,
            "carbs": 0
        },
        "allergens": ["dairy"],
        "dietary_flags": ["high_fat", "high_saturated_fat"],
        "price": 4.99,
        "image_url": "https://example.com/butter.jpg"
    },
    "WALMART_005": {
        "id": "WALMART_005",
        "name": "Earth Balance Vegan Buttery Spread",
        "brand": "Earth Balance",
        "category": "Dairy",
        "ingredients": ["vegetable oil blend", "water", "salt", "natural flavor"],
        "nutrition": {
            "calories": 100,
            "total_fat": 11,
            "saturated_fat": 3.5,
            "protein": 0,
            "carbs": 0
        },
        "allergens": ["soy"],
        "dietary_flags": ["high_fat"],
        "price": 5.99,
        "image_url": "https://example.com/earth-balance.jpg"
    }
}

# Sample user profiles with preferences and restrictions
USER_PROFILES = {
    "user_001": {
        "id": "user_001",
        "name": "John Doe",
        "allergies": ["peanuts", "tree_nuts"],
        "dietary_preferences": ["low_fat", "low_calories"],
        "restrictions": ["high_saturated_fat"],
        "preferred_brands": ["Silk", "SunButter"],
        "avoid_brands": ["Jif"],
        "budget_preference": "moderate"
    },
    "user_002": {
        "id": "user_002", 
        "name": "Jane Smith",
        "allergies": ["dairy"],
        "dietary_preferences": ["vegan", "low_fat"],
        "restrictions": ["high_fat"],
        "preferred_brands": ["Silk", "Earth Balance"],
        "avoid_brands": ["Land O'Lakes"],
        "budget_preference": "budget"
    }
}

class QRScanRequest(BaseModel):
    qr_code_data: str
    user_id: str

class ProductAnalysis(BaseModel):
    product_id: str
    product_name: str
    is_safe: bool
    safety_score: float
    warnings: List[str]
    alternatives: List[Dict]
    nutrition_analysis: Dict
    price_comparison: Dict

def analyze_product_safety(product: Dict, user_profile: Dict) -> Dict:
    """
    Analyze if a product is safe for a user based on their preferences and restrictions
    """
    warnings = []
    safety_score = 100.0
    issues_found = 0
    
    # Check allergies
    for allergen in user_profile.get("allergies", []):
        if allergen.lower() in [a.lower() for a in product.get("allergens", [])]:
            warnings.append(f"⚠️ CONTAINS {allergen.upper()} - ALLERGIC REACTION RISK")
            safety_score -= 50
            issues_found += 1
    
    # Check dietary restrictions
    for restriction in user_profile.get("restrictions", []):
        if restriction in product.get("dietary_flags", []):
            warnings.append(f"⚠️ HIGH {restriction.replace('_', ' ').upper()} CONTENT")
            safety_score -= 20
            issues_found += 1
    
    # Check brand preferences
    if product.get("brand") in user_profile.get("avoid_brands", []):
        warnings.append(f"⚠️ AVOIDED BRAND: {product['brand']}")
        safety_score -= 15
        issues_found += 1
    
    # Check nutrition preferences
    nutrition = product.get("nutrition", {})
    if "low_fat" in user_profile.get("dietary_preferences", []):
        if nutrition.get("total_fat", 0) > 5:
            warnings.append(f"⚠️ HIGH FAT: {nutrition.get('total_fat', 0)}g per serving")
            safety_score -= 10
            issues_found += 1
    
    if "low_calories" in user_profile.get("dietary_preferences", []):
        if nutrition.get("calories", 0) > 150:
            warnings.append(f"⚠️ HIGH CALORIES: {nutrition.get('calories', 0)} per serving")
            safety_score -= 10
            issues_found += 1
    
    # Ensure safety score doesn't go below 0
    safety_score = max(0, safety_score)
    
    return {
        "is_safe": safety_score >= 70,
        "safety_score": safety_score,
        "warnings": warnings,
        "issues_found": issues_found
    }

def find_alternatives(product: Dict, user_profile: Dict, max_alternatives: int = 3) -> List[Dict]:
    """
    Find alternative products that are safe for the user
    """
    alternatives = []
    
    for product_id, alt_product in PRODUCTS_DATABASE.items():
        if product_id == product["id"]:
            continue  # Skip the original product
            
        # Check if alternative is safe
        safety_analysis = analyze_product_safety(alt_product, user_profile)
        
        if safety_analysis["is_safe"] and safety_analysis["safety_score"] >= 80:
            # Calculate relevance score based on category and preferences
            relevance_score = 0
            
            # Same category gets points
            if alt_product.get("category") == product.get("category"):
                relevance_score += 30
            
            # Preferred brands get points
            if alt_product.get("brand") in user_profile.get("preferred_brands", []):
                relevance_score += 20
            
            # Lower price gets points for budget users
            if user_profile.get("budget_preference") == "budget":
                if alt_product.get("price", 0) < product.get("price", 0):
                    relevance_score += 15
            
            # Lower fat/calories gets points for health-conscious users
            if "low_fat" in user_profile.get("dietary_preferences", []):
                if alt_product.get("nutrition", {}).get("total_fat", 0) < product.get("nutrition", {}).get("total_fat", 0):
                    relevance_score += 10
            
            alternatives.append({
                "product_id": alt_product["id"],
                "name": alt_product["name"],
                "brand": alt_product["brand"],
                "price": alt_product["price"],
                "safety_score": safety_analysis["safety_score"],
                "relevance_score": relevance_score,
                "why_safe": f"Safe alternative: {', '.join(safety_analysis['warnings'])}" if not safety_analysis['warnings'] else "No warnings"
            })
    
    # Sort by relevance score and return top alternatives
    alternatives.sort(key=lambda x: x["relevance_score"], reverse=True)
    return alternatives[:max_alternatives]

def analyze_nutrition(product: Dict, user_profile: Dict) -> Dict:
    """
    Analyze nutrition information against user preferences
    """
    nutrition = product.get("nutrition", {})
    analysis = {
        "overall_health_score": 100,
        "recommendations": [],
        "nutrition_highlights": {}
    }
    
    # Check fat content
    total_fat = nutrition.get("total_fat", 0)
    saturated_fat = nutrition.get("saturated_fat", 0)
    
    if "low_fat" in user_profile.get("dietary_preferences", []):
        if total_fat > 5:
            analysis["recommendations"].append("Consider lower-fat alternatives")
            analysis["overall_health_score"] -= 20
        if saturated_fat > 3:
            analysis["recommendations"].append("High in saturated fat")
            analysis["overall_health_score"] -= 15
    
    # Check calories
    calories = nutrition.get("calories", 0)
    if "low_calories" in user_profile.get("dietary_preferences", []):
        if calories > 150:
            analysis["recommendations"].append("High calorie content")
            analysis["overall_health_score"] -= 15
    
    # Nutrition highlights
    analysis["nutrition_highlights"] = {
        "fat_content": f"{total_fat}g total fat",
        "calories": f"{calories} calories",
        "protein": f"{nutrition.get('protein', 0)}g protein"
    }
    
    return analysis

@app.post("/scan-qr/", summary="Scan QR code and analyze product safety")
async def scan_qr_code(request: QRScanRequest):
    """
    Scan a QR code, fetch product details, and analyze safety against user preferences
    """
    try:
        # Extract product ID from QR code data
        # In real implementation, this would parse the QR code data
        product_id = request.qr_code_data.strip()
        
        # Get user profile
        user_profile = USER_PROFILES.get(request.user_id)
        if not user_profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Get product details
        product = PRODUCTS_DATABASE.get(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found in database")
        
        # Analyze product safety
        safety_analysis = analyze_product_safety(product, user_profile)
        
        # Find alternatives if product is unsafe
        alternatives = []
        if not safety_analysis["is_safe"]:
            alternatives = find_alternatives(product, user_profile)
        
        # Analyze nutrition
        nutrition_analysis = analyze_nutrition(product, user_profile)
        
        # Price comparison with alternatives
        price_comparison = {
            "current_price": product.get("price", 0),
            "average_alternative_price": sum(alt["price"] for alt in alternatives) / len(alternatives) if alternatives else 0,
            "budget_friendly": any(alt["price"] < product.get("price", 0) for alt in alternatives)
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "product": {
                    "id": product["id"],
                    "name": product["name"],
                    "brand": product["brand"],
                    "category": product["category"],
                    "price": product["price"],
                    "ingredients": product["ingredients"],
                    "nutrition": product["nutrition"],
                    "allergens": product["allergens"]
                },
                "safety_analysis": safety_analysis,
                "nutrition_analysis": nutrition_analysis,
                "alternatives": alternatives,
                "price_comparison": price_comparison,
                "recommendation": "SAFE TO CONSUME" if safety_analysis["is_safe"] else "AVOID - Check alternatives below"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing QR code: {str(e)}")

@app.get("/user-profile/{user_id}", summary="Get user profile")
async def get_user_profile(user_id: str):
    """
    Get user profile with preferences and restrictions
    """
    user_profile = USER_PROFILES.get(user_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    return JSONResponse(
        status_code=200,
        content={"user_profile": user_profile}
    )

@app.post("/update-user-profile/{user_id}", summary="Update user profile")
async def update_user_profile(user_id: str, profile_update: Dict):
    """
    Update user profile with new preferences or restrictions
    """
    if user_id not in USER_PROFILES:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Update profile (in real implementation, this would save to database)
    USER_PROFILES[user_id].update(profile_update)
    
    return JSONResponse(
        status_code=200,
        content={"message": "Profile updated successfully", "user_profile": USER_PROFILES[user_id]}
    )

@app.get("/products/", summary="Get all products")
async def get_all_products():
    """
    Get all products in database (for testing)
    """
    return JSONResponse(
        status_code=200,
        content={"products": PRODUCTS_DATABASE}
    )

# QR Code generation utility (for testing)
@app.post("/generate-qr/{product_id}", summary="Generate QR code for product")
async def generate_qr_code(product_id: str):
    """
    Generate a QR code for a product (useful for testing)
    """
    if product_id not in PRODUCTS_DATABASE:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(product_id)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to file (in real implementation, this would return the image)
    filename = f"qr_{product_id}.png"
    img.save(filename)
    
    return JSONResponse(
        status_code=200,
        content={
            "message": f"QR code generated for {product_id}",
            "filename": filename,
            "qr_data": product_id
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 