from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv
import json
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure OpenAI
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    logger.error("OPENAI_API_KEY environment variable is not set!")
    client_configured = False
else:
    logger.info("OPENAI_API_KEY is configured")
    try:
        openai.api_key = openai_api_key
        client_configured = True
        logger.info("OpenAI client configured successfully")
    except Exception as e:
        logger.error(f"Failed to configure OpenAI client: {e}")
        client_configured = False

# Location validation function
def is_valid_location(location):
    """Check if location is a real, accessible place"""
    # Common invalid locations
    invalid_locations = [
        "mars", "moon", "jupiter", "saturn", "venus", "mercury", "neptune", "uranus", "pluto",
        "hogwarts", "middle earth", "narnia", "westeros", "neverland", "atlantis", "el dorado",
        "shangri-la", "utopia", "fantasy land", "dream world", "imaginary place", "fake city",
        "test location", "example city", "sample town", "demo place", "mock location"
    ]
    
    location_lower = location.lower().strip()
    
    # Check against invalid locations
    for invalid in invalid_locations:
        if invalid in location_lower:
            return False
    
    # Check if location is too short or generic
    if len(location.strip()) < 3:
        return False
    
    # Check for obvious non-locations
    if any(word in location_lower for word in ["test", "example", "sample", "demo", "fake", "mock"]):
        return False
    
    return True

# Category-specific system prompts
CATEGORY_PROMPTS = {
    "date": """You are a specialized Date Ideas Expert. You generate romantic, memorable, and engaging date activities for couples.

Your expertise includes:
- Romantic dining experiences and unique restaurants
- Cultural activities (museums, theaters, galleries)
- Outdoor adventures and scenic locations
- Entertainment venues and shows
- Wellness and relaxation activities
- Creative and interactive experiences

Focus on activities that:
- Foster connection and conversation
- Create memorable moments
- Are suitable for couples
- Offer variety in price ranges
- Include both indoor and outdoor options

PRICING GUIDELINES:
- Research and provide accurate price estimates when possible
- Use specific ranges like "$15-25 per person" instead of just "$"
- For restaurants, include typical meal costs
- For activities, include per-person costs
- For free activities, use "$0" or "Free"
- For premium experiences, use specific ranges like "$150-300 per couple"

HOURS GUIDELINES:
- Provide accurate, current operating hours
- Include days of the week when relevant
- Note seasonal variations if applicable
- Include special hours for holidays or events
- Use format: "Mon-Fri 9am-5pm, Sat-Sun 10am-6pm"

IMPORTANT: Only suggest activities that actually exist in the specified location. If the location is invalid or fictional, respond with an error message.""",

    "travel": """You are a specialized Travel Activities Expert. You generate exciting travel experiences and adventures for tourists and travelers.

Your expertise includes:
- Tourist attractions and landmarks
- Adventure activities and outdoor experiences
- Cultural immersion and local experiences
- Food and culinary tours
- Historical sites and educational activities
- Entertainment and nightlife
- Shopping and markets
- Transportation and sightseeing

Focus on activities that:
- Showcase the destination's unique character
- Appeal to travelers and tourists
- Offer authentic local experiences
- Include both popular and hidden gems
- Cater to different interests and budgets

PRICING GUIDELINES:
- Research and provide accurate price estimates when possible
- Use specific ranges like "$25-45 per person" instead of just "$"
- For attractions, include admission fees
- For tours, include per-person costs
- For free attractions, use "$0" or "Free"
- For premium experiences, use specific ranges like "$80-150 per person"

HOURS GUIDELINES:
- Provide accurate, current operating hours
- Include days of the week when relevant
- Note seasonal variations if applicable
- Include special hours for holidays or events
- Use format: "Mon-Fri 9am-5pm, Sat-Sun 10am-6pm"

IMPORTANT: Only suggest activities that actually exist in the specified location. If the location is invalid or fictional, respond with an error message.""",

    "local": """You are a specialized Local Activities Expert. You generate engaging activities for residents and locals to enjoy their own city.

Your expertise includes:
- Local entertainment and recreation
- Community events and activities
- Fitness and wellness options
- Educational and skill-building activities
- Social and networking opportunities
- Family-friendly activities
- Hobby and interest groups
- Local businesses and services

Focus on activities that:
- Help locals discover their city
- Build community connections
- Support local businesses
- Offer regular and ongoing options
- Appeal to different age groups and interests

PRICING GUIDELINES:
- Research and provide accurate price estimates when possible
- Use specific ranges like "$10-20 per class" instead of just "$"
- For classes, include per-session costs
- For memberships, include monthly/annual fees
- For free activities, use "$0" or "Free"
- For premium services, use specific ranges like "$50-100 per session"

HOURS GUIDELINES:
- Provide accurate, current operating hours
- Include days of the week when relevant
- Note seasonal variations if applicable
- Include special hours for holidays or events
- Use format: "Mon-Fri 9am-5pm, Sat-Sun 10am-6pm"

IMPORTANT: Only suggest activities that actually exist in the specified location. If the location is invalid or fictional, respond with an error message.""",

    "special": """You are a specialized Special Events Expert. You generate unique and memorable experiences for celebrations and special occasions.

Your expertise includes:
- Birthday celebrations and parties
- Anniversary and milestone events
- Holiday and seasonal activities
- Corporate events and team building
- Graduation and achievement celebrations
- Engagement and wedding activities
- Holiday and vacation experiences
- Cultural and religious celebrations

Focus on activities that:
- Make occasions memorable and special
- Create lasting memories
- Offer unique and exclusive experiences
- Cater to different group sizes
- Include both intimate and grand celebrations

PRICING GUIDELINES:
- Research and provide accurate price estimates when possible
- Use specific ranges like "$200-500 for group of 10" instead of just "$"
- For venues, include rental costs
- For services, include per-person or package costs
- For premium experiences, use specific ranges like "$500-1500 per event"
- Include what's included in the price when relevant

HOURS GUIDELINES:
- Provide accurate, current operating hours
- Include days of the week when relevant
- Note seasonal variations if applicable
- Include special hours for holidays or events
- Use format: "Mon-Fri 9am-5pm, Sat-Sun 10am-6pm"

IMPORTANT: Only suggest activities that actually exist in the specified location. If the location is invalid or fictional, respond with an error message.""",

    "group": """You are a specialized Group Activities Expert. You generate fun and engaging activities for groups of friends, families, or teams.

Your expertise includes:
- Team building and group bonding activities
- Social gatherings and parties
- Family-friendly group activities
- Sports and recreational group activities
- Educational and cultural group experiences
- Entertainment and gaming activities
- Food and dining group experiences
- Adventure and outdoor group activities

Focus on activities that:
- Bring people together
- Encourage interaction and collaboration
- Appeal to diverse group interests
- Work for different group sizes
- Offer both competitive and cooperative options

PRICING GUIDELINES:
- Research and provide accurate price estimates when possible
- Use specific ranges like "$30-60 per person" instead of just "$"
- For group activities, include per-person costs
- For team building, include package prices
- For family activities, include family rates when available
- For premium experiences, use specific ranges like "$75-150 per person"

HOURS GUIDELINES:
- Provide accurate, current operating hours
- Include days of the week when relevant
- Note seasonal variations if applicable
- Include special hours for holidays or events
- Use format: "Mon-Fri 9am-5pm, Sat-Sun 10am-6pm"

IMPORTANT: Only suggest activities that actually exist in the specified location. If the location is invalid or fictional, respond with an error message."""
}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "adoreventure-ai-backend"})

@app.route('/test-env', methods=['GET'])
def test_env():
    """Test environment variables"""
    return jsonify({
        "openai_key_set": bool(openai_api_key),
        "openai_key_length": len(openai_api_key) if openai_api_key else 0,
        "flask_env": os.getenv('FLASK_ENV', 'not_set'),
        "client_configured": client_configured
    })

@app.route('/api/ideas', methods=['POST'])
def get_ideas():
    """Generate adventure ideas using OpenAI"""
    try:
        # Check if OpenAI API key is configured
        if not openai_api_key:
            logger.error("OPENAI_API_KEY is not configured")
            return jsonify({"error": "OpenAI API key not configured"}), 500

        # Check if client is configured
        if not client_configured:
            logger.error("OpenAI client is not configured")
            return jsonify({"error": "OpenAI client not configured"}), 500

        # Get request data
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Extract parameters
        location = data.get('location', '')
        category = data.get('category', '')
        budget_hint = data.get('budgetHint', '')
        time_hint = data.get('timeHint', '')
        indoor_outdoor = data.get('indoorOutdoor', '')

        if not location or not category:
            return jsonify({"error": "Location and category are required"}), 400

        # Validate location
        if not is_valid_location(location):
            return jsonify({"error": f"'{location}' is not a valid location. Please enter a real city, town, or area."}), 400

        # Get category-specific system prompt
        system_prompt = CATEGORY_PROMPTS.get(category.lower(), CATEGORY_PROMPTS["local"])
        
        # Add JSON output format to system prompt
        system_prompt += """

You generate activity ideas as STRICT JSON only.
Output MUST be a JSON object with this exact shape:

{
  "ideas": [
    {
      "title": "String",
      "blurb": "Short enticing description (1–2 sentences).",
      "rating": 4.3,
      "place": "Neighborhood or venue name",
      "duration": "e.g. 1–3 hours",
      "priceRange": "Specific price range like $15-25 per person or Free",
      "tags": ["short","tag","words"],

      // Detail fields (optional but preferred; use null if unknown)
      "address": "Full address or area, city/state",
      "phone": "(202) 555-0199",
      "website": "https://example.com",
      "bookingURL": "https://booking.example.com",
      "bestTime": "e.g. Golden hour 6–8 pm",
      "hours": ["Mon–Thu 10am–9pm","Fri–Sat 10am–11pm","Sun 10am–8pm"]
    }
  ]
}

IMPORTANT REQUIREMENTS:
- priceRange: Use specific ranges like "$15-25 per person", "$0" for free, or "Free"
- hours: Provide accurate, current operating hours in format ["Mon-Fri 9am-5pm", "Sat-Sun 10am-6pm"]
- Only suggest activities that actually exist in the specified location
- Ratings must be between 4.3 and 5.0
- Return 6–10 ideas"""

        # Build user prompt
        user_prompt = f"""
Location: {location}
Category: {category}
Preferences:
{f"Budget: {budget_hint}" if budget_hint else "-"}
{f"Time: {time_hint}" if time_hint else "-"}
{f"Setting: {indoor_outdoor}" if indoor_outdoor else "-"}

Generate activities that are specific to {location} and relevant to the {category} category.
Ensure all suggestions are real, accessible places and activities in {location}.
"""

        logger.info(f"Generating {category} ideas for location: {location}")

        # Call OpenAI API using old syntax
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        # Extract and parse response
        content = response.choices[0].message.content
        ideas_data = json.loads(content)

        logger.info(f"Successfully generated {len(ideas_data.get('ideas', []))} {category} ideas for {location}")

        return jsonify(ideas_data)

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return jsonify({"error": "Invalid JSON response from AI"}), 500
    except Exception as e:
        logger.error(f"Error generating ideas: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/api/ideas/test', methods=['GET'])
def test_ideas():
    """Test endpoint with sample data"""
    sample_ideas = {
        "ideas": [
            {
                "title": "Sunset Kayaking Adventure",
                "blurb": "Paddle through calm waters while watching the sun set over the horizon.",
                "rating": 4.8,
                "place": "Harbor Point Marina",
                "duration": "2-3 hours",
                "priceRange": "$$",
                "tags": ["outdoor", "water", "sunset", "romantic"],
                "address": "123 Harbor Drive, Washington DC",
                "phone": "(202) 555-0123",
                "website": "https://harborpoint.com",
                "bookingURL": "https://harborpoint.com/book",
                "bestTime": "Golden hour 6-8 pm",
                "hours": ["Mon-Sun 9am-9pm"]
            }
        ]
    }
    return jsonify(sample_ideas)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
