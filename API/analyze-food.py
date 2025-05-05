from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
import os
import io
import base64
import requests
from PIL import Image
from dotenv import load_dotenv
from google.cloud import vision
import torch
from transformers import CLIPProcessor, CLIPModel

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Food Analysis API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Google Vision API client
def setup_google_vision():
    """Set up Google Vision client with error handling"""
    try:
        # For Vercel serverless, use credentials JSON content from environment variable
        google_credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if not google_credentials_json:
            raise ValueError("GOOGLE_CREDENTIALS_JSON is not set in environment variables.")
        
        # Create credentials from JSON content
        credentials_info = json.loads(google_credentials_json)
        vision_client = vision.ImageAnnotatorClient.from_service_account_info(credentials_info)
        return vision_client
    except Exception as e:
        logger.error(f"Error setting up Google Vision: {e}")
        raise

# Load CLIP model with error handling
def setup_clip_model():
    """Set up CLIP model with error handling"""
    try:
        clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        return clip_model, clip_processor
    except Exception as e:
        logger.error(f"Error loading CLIP model: {e}")
        raise

# Validate API keys
def validate_api_keys():
    """Validate required API keys"""
    required_keys = ["USDA_API_KEY", "GOOGLE_CREDENTIALS_JSON"]
    for key in required_keys:
        if not os.getenv(key):
            raise ValueError(f"{key} is not set in environment variables.")

# Initialize global variables
try:
    validate_api_keys()
    vision_client = setup_google_vision()
    clip_model, clip_processor = setup_clip_model()
    
    # USDA API credentials
    USDA_API_KEY = os.getenv("USDA_API_KEY")
    USDA_API_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
except Exception as e:
    logger.error(f"Initialization error: {e}")
    vision_client = None
    clip_model = None
    clip_processor = None
    USDA_API_KEY = None
    USDA_API_URL = None

# Function to get food items using Google Vision API
def detect_food_vision(image_bytes):
    """Detects food items in an image using Google Vision API"""
    try:
        image = vision.Image(content=image_bytes)
        response = vision_client.label_detection(image=image)
        labels = response.label_annotations
        
        # Filter and sort food-related labels
        food_items = [
            label.description 
            for label in labels 
            if label.score > 0.6 and any(food in label.description.lower() for food in [
                'food', 'fruit', 'vegetable', 'meat', 'fish', 'bread', 'cheese', 'drink'
            ])
        ]
        
        return food_items[:5] if food_items else ["No specific food detected"]
    except Exception as e:
        logger.error(f"Vision API error: {e}")
        return [f"Error in Vision API: {str(e)}"]

# Function to classify ingredients using CLIP
def classify_ingredients(image_bytes):
    """Classifies main ingredient using CLIP"""
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        food_labels = [
            "apple", "banana", "bread", "pasta", 
            "chicken", "salad", "cheese", "rice", 
            "fish", "steak", "tomato", "broccoli", 
            "carrot", "salmon", "burger"
        ]

        inputs = clip_processor(text=food_labels, images=image, return_tensors="pt", padding=True)
        outputs = clip_model(**inputs)
        logits_per_image = outputs.logits_per_image
        probs = logits_per_image.softmax(dim=1)

        top_ingredient_index = torch.argmax(probs)
        top_ingredient = food_labels[top_ingredient_index]
        confidence = probs[0][top_ingredient_index].item()

        logger.info(f"Classified ingredient: {top_ingredient} with confidence: {confidence}")
        return top_ingredient
    except Exception as e:
        logger.error(f"CLIP Model error: {e}")
        return f"Error in CLIP Model: {str(e)}"

# Function to fetch nutrition data
def get_nutrition_data(ingredient):
    """Fetches nutrition data for a given ingredient"""
    try:
        response = requests.get(f"{USDA_API_URL}?query={ingredient}&api_key={USDA_API_KEY}")

        if response.status_code == 200:
            data = response.json()
            if "foods" in data and data["foods"]:
                food = data["foods"][0]
                nutrients = {
                    nutrient["nutrientName"]: nutrient["value"] 
                    for nutrient in food.get("foodNutrients", [])
                }

                return {
                    "name": food["description"],
                    "calories": round(nutrients.get("Energy (kcal)", 0), 2),
                    "protein": round(nutrients.get("Protein", 0), 2),
                    "carbs": round(nutrients.get("Carbohydrate, by difference", 0), 2),
                    "fats": round(nutrients.get("Total lipid (fat)", 0), 2),
                }
        return {"error": "No nutrition data found"}
    except Exception as e:
        logger.error(f"Nutrition data fetch error: {e}")
        return {"error": f"Failed to fetch nutrition data: {str(e)}"}

# Function to suggest healthier alternatives
def suggest_alternative(food_item):
    """Suggests a healthier alternative for a given food item"""
    alternatives = {
        "pasta": "Try zucchini noodles or whole wheat pasta for fewer calories and more nutrients.",
        "chicken": "Consider grilled tofu or salmon for lean protein with healthy omega-3 fatty acids.",
        "bread": "Opt for whole grain or sourdough bread with more fiber and lower glycemic index.",
        "banana": "Try mixed berries or an apple for lower sugar content and more varied nutrients.",
        "cheese": "Choose low-fat cheese or nutritional yeast for a healthier, protein-rich alternative.",
        "rice": "Swap with quinoa or cauliflower rice for higher protein and lower carbohydrate content.",
        "steak": "Try lean turkey, grilled fish, or plant-based protein for a heart-healthy option.",
    }
    return alternatives.get(food_item.lower(), "No specific alternative found. Consider consulting a nutritionist for personalized advice.")

# Vercel serverless function handler
@app.post("/api/analyze-food")
async def analyze_food(request: Request):
    """Serverless function endpoint for food image analysis"""
    try:
        # Parse form data from request
        form_data = await request.form()
        image_file = form_data.get("image")
        
        if not image_file:
            return {"error": "No image file provided"}
        
        # Read image bytes
        image_bytes = await image_file.read()
        
        # Detect food using Google Vision API
        detected_food = detect_food_vision(image_bytes)
        logger.info(f"Detected foods: {detected_food}")
        
        # Classify main ingredient using CLIP
        main_ingredient = classify_ingredients(image_bytes)
        logger.info(f"Main ingredient: {main_ingredient}")
        
        # Get nutrition data
        nutrition_info = get_nutrition_data(main_ingredient)
        logger.info(f"Nutrition info: {nutrition_info}")
        
        # Suggest a healthier alternative
        alternative_suggestion = suggest_alternative(main_ingredient)
        logger.info(f"Alternative suggestion: {alternative_suggestion}")
        
        return {
            "detected_food": detected_food,
            "main_ingredient": main_ingredient,
            "nutrition_info": nutrition_info,
            "healthier_alternative": alternative_suggestion
        }
    
    except Exception as e:
        logger.error(f"Unexpected error in food analysis: {e}")
        return {"error": str(e)}

# For development purposes
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)