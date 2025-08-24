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
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "adoreventure-ai-backend"})

@app.route('/api/ideas', methods=['POST'])
def get_ideas():
    """Generate adventure ideas using OpenAI"""
    try:
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

        logger.info(f"Generating ideas for location: {location}, category: {category}")

        # Build system prompt
        system_prompt = """
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
              "priceRange": "$$",
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

        Do not include any text outside JSON.
        Ratings must be between 4.3 and 5.0. Return 6–10 ideas.
        """

        # Build user prompt
        user_prompt = f"""
        Location: {location}
        Category: {category}
        Preferences:
        {f"Budget: {budget_hint}" if budget_hint else "-"}
        {f"Time: {time_hint}" if time_hint else "-"}
        {f"Setting: {indoor_outdoor}" if indoor_outdoor else "-"}
        Return only activities relevant to the location/category.
        """

        # Call OpenAI API
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

        logger.info(f"Successfully generated {len(ideas_data.get('ideas', []))} ideas")

        return jsonify(ideas_data)

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return jsonify({"error": "Invalid JSON response from AI"}), 500
    except Exception as e:
        logger.error(f"Error generating ideas: {e}")
        return jsonify({"error": "Internal server error"}), 500

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
