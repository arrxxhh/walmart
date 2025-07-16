#!/usr/bin/env python3
"""
Test script for the QR Scanner System
"""

import requests
import json

def test_qr_scanner():
    """Test the QR scanner API"""
    
    API_BASE_URL = "http://localhost:8001"
    
    print("🧪 Testing QR Scanner System...")
    print("=" * 50)
    
    # Test 1: Get user profile
    print("\n1️⃣ Testing User Profile...")
    try:
        response = requests.get(f"{API_BASE_URL}/user-profile/user_001")
        if response.status_code == 200:
            profile = response.json()["user_profile"]
            print(f"✅ User Profile: {profile['name']}")
            print(f"   Allergies: {profile['allergies']}")
            print(f"   Preferences: {profile['dietary_preferences']}")
        else:
            print(f"❌ Failed to get user profile: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Scan unsafe product (peanut butter)
    print("\n2️⃣ Testing Unsafe Product (Peanut Butter)...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/scan-qr/",
            json={"qr_code_data": "WALMART_001", "user_id": "user_001"}
        )
        if response.status_code == 200:
            result = response.json()
            product = result["product"]
            safety = result["safety_analysis"]
            
            print(f"✅ Product: {product['name']}")
            print(f"   Safety: {'❌ Unsafe' if not safety['is_safe'] else '✅ Safe'}")
            print(f"   Safety Score: {safety['safety_score']:.0f}/100")
            print(f"   Warnings: {safety['warnings']}")
            print(f"   Alternatives: {len(result['alternatives'])} found")
            
            if result["alternatives"]:
                print("   Top Alternative:")
                alt = result["alternatives"][0]
                print(f"     • {alt['name']} (${alt['price']:.2f}) - Score: {alt['safety_score']:.0f}")
        else:
            print(f"❌ Failed to scan product: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Scan safe product (sunflower butter)
    print("\n3️⃣ Testing Safe Product (SunButter)...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/scan-qr/",
            json={"qr_code_data": "WALMART_002", "user_id": "user_001"}
        )
        if response.status_code == 200:
            result = response.json()
            product = result["product"]
            safety = result["safety_analysis"]
            
            print(f"✅ Product: {product['name']}")
            print(f"   Safety: {'❌ Unsafe' if not safety['is_safe'] else '✅ Safe'}")
            print(f"   Safety Score: {safety['safety_score']:.0f}/100")
            print(f"   Warnings: {safety['warnings']}")
        else:
            print(f"❌ Failed to scan product: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Test dairy allergy user
    print("\n4️⃣ Testing Dairy Allergy User...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/scan-qr/",
            json={"qr_code_data": "WALMART_004", "user_id": "user_002"}
        )
        if response.status_code == 200:
            result = response.json()
            product = result["product"]
            safety = result["safety_analysis"]
            
            print(f"✅ Product: {product['name']}")
            print(f"   Safety: {'❌ Unsafe' if not safety['is_safe'] else '✅ Safe'}")
            print(f"   Safety Score: {safety['safety_score']:.0f}/100")
            print(f"   Warnings: {safety['warnings']}")
        else:
            print(f"❌ Failed to scan product: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Testing Complete!")
    print("\n📱 To test the full UI:")
    print("1. Backend is running on: http://localhost:8001")
    print("2. Frontend is running on: http://localhost:8501")
    print("3. Open http://localhost:8501 in your browser")
    print("4. Try the 'Quick Test Products' buttons")

if __name__ == "__main__":
    test_qr_scanner() 