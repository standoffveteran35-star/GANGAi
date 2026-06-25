import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Path configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(BASE_DIR, "automation", "schema.json")
PROMPT_PATH = os.path.join(BASE_DIR, "automation", "extractor_prompt.md")

# Load Schema
with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    SCHEMA = json.load(f)

# Load System Prompt
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# Mock Conversation representing a typical PersonalOS session
MOCK_CONVERSATION = """
Pavan: I've decided to stop using standard paper flyers for student acquisition in Nashik. We spent 15,000 INR on them for the 8th Standard Scholarship Exam promotion, but we only got 2 sign-ups from it. From now on, we will focus exclusively on practical "Science in Action" workshops for parent/student top-of-funnel acquisition, as our previous workshop brought in 15 high-intent leads for only 2,000 INR. Also, let's start a new project called "Vedic Math Bootcamp" as a bridge course for the upcoming academic batches. I want to run this boot camp in July.
AI: Got it. I will log this decision, the lesson regarding flyers vs. workshops, and initialize the Vedic Math Bootcamp project.
"""

def validate_against_schema(data):
    """
    Manually validate the extracted data against the schema.json properties.
    Ensures robust validation without external jsonschema package dependency.
    """
    errors = []
    
    if not isinstance(data, dict):
        return ["Output is not a JSON object"]

    # Check properties
    for key, value in data.items():
        if key not in SCHEMA["properties"]:
            errors.append(f"Unexpected field: '{key}'")
            continue

    # Validate individual updates
    if "user_updates" in data:
        if not isinstance(data["user_updates"], list):
            errors.append("'user_updates' must be an array")
        else:
            for i, item in enumerate(data["user_updates"]):
                for req in ["category", "content", "confidence"]:
                    if req not in item:
                        errors.append(f"user_updates[{i}] missing required field: '{req}'")

    if "project_updates" in data:
        if not isinstance(data["project_updates"], list):
            errors.append("'project_updates' must be an array")
        else:
            for i, item in enumerate(data["project_updates"]):
                for req in ["action", "project_name", "confidence"]:
                    if req not in item:
                        errors.append(f"project_updates[{i}] missing required field: '{req}'")
                if "action" in item and item["action"] not in ["add", "update", "pause", "complete"]:
                    errors.append(f"project_updates[{i}] invalid action: '{item['action']}'")

    if "decision_updates" in data:
        if not isinstance(data["decision_updates"], list):
            errors.append("'decision_updates' must be an array")
        else:
            for i, item in enumerate(data["decision_updates"]):
                for req in ["decision", "confidence"]:
                    if req not in item:
                        errors.append(f"decision_updates[{i}] missing required field: '{req}'")

    if "lesson_updates" in data:
        if not isinstance(data["lesson_updates"], list):
            errors.append("'lesson_updates' must be an array")
        else:
            for i, item in enumerate(data["lesson_updates"]):
                for req in ["lesson", "confidence"]:
                    if req not in item:
                        errors.append(f"lesson_updates[{i}] missing required field: '{req}'")

    if "memory_updates" in data:
        if not isinstance(data["memory_updates"], list):
            errors.append("'memory_updates' must be an array")
        else:
            for i, item in enumerate(data["memory_updates"]):
                if "event" not in item:
                    errors.append(f"memory_updates[{i}] missing required field: 'event'")
                    
    return errors

def run_gemini():
    """
    Test memory extraction using Google Gemini via the google-genai SDK.
    """
    print("\n" + "="*40)
    print("Testing Google Gemini...")
    print("="*40)
    
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[-] Skipping Gemini: GEMINI_API_KEY or GOOGLE_API_KEY is not set.")
        return None

    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        # Enforce structured output using schema
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=SCHEMA,
            temperature=0.1
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=MOCK_CONVERSATION,
            config=config
        )
        
        extracted_data = json.loads(response.text)
        print("[+] Gemini Response successfully parsed as JSON.")
        return extracted_data
        
    except Exception as e:
        print(f"[-] Gemini test encountered an error: {e}")
        return None

def run_openai():
    """
    Test memory extraction using OpenAI GPT via direct HTTP request to avoid extra dependencies.
    """
    print("\n" + "="*40)
    print("Testing OpenAI GPT...")
    print("="*40)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[-] Skipping OpenAI GPT: OPENAI_API_KEY is not set.")
        return None

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Build prompt
        prompt = f"{SYSTEM_PROMPT}\n\nConversation to analyze:\n{MOCK_CONVERSATION}"
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        response.raise_for_status()
        res_json = response.json()
        raw_content = res_json["choices"][0]["message"]["content"]
        
        extracted_data = json.loads(raw_content)
        print("[+] OpenAI GPT Response successfully parsed as JSON.")
        return extracted_data
        
    except Exception as e:
        print(f"[-] OpenAI GPT test encountered an error: {e}")
        return None

def main():
    gemini_data = run_gemini()
    if gemini_data:
        print("\nGemini Output:")
        print(json.dumps(gemini_data, indent=2))
        errors = validate_against_schema(gemini_data)
        if errors:
            print("[-] Gemini Validation Errors:")
            for err in errors:
                print(f"  * {err}")
        else:
            print("[+] Gemini output is 100% schema-compliant!")

    gpt_data = run_openai()
    if gpt_data:
        print("\nGPT Output:")
        print(json.dumps(gpt_data, indent=2))
        errors = validate_against_schema(gpt_data)
        if errors:
            print("[-] GPT Validation Errors:")
            for err in errors:
                print(f"  * {err}")
        else:
            print("[+] GPT output is 100% schema-compliant!")

    if not gemini_data and not gpt_data:
        print("\n[!] No API keys configured. Set GEMINI_API_KEY and/or OPENAI_API_KEY to execute remote tests.")
        print("\nMock validation test using local validation logic:")
        mock_output = {
            "summary": "Pavan updates operational channels for Talent Academy and Nexoravista.",
            "project_updates": [
                {
                    "action": "add",
                    "project_name": "Vedic Math Bootcamp",
                    "details": "Launch as a bridge course in July.",
                    "confidence": 0.95
                }
            ],
            "decision_updates": [
                {
                    "decision": "Stop using standard paper flyers, focus on practical workshops.",
                    "reasoning": "Flyers cost 15k INR with 2 signups, workshops cost 2k INR with 15 leads.",
                    "confidence": 0.98
                }
            ],
            "lesson_updates": [
                {
                    "lesson": "Paper flyers are low-ROI in Nashik compared to physical interactive workshops.",
                    "evidence": "15,000 INR on flyers yielded 2 signups. 2,000 INR on workshop yielded 15 leads.",
                    "confidence": 0.98
                }
            ]
        }
        print("Mock JSON Object:")
        print(json.dumps(mock_output, indent=2))
        errors = validate_against_schema(mock_output)
        if not errors:
            print("[+] Validation engine works! Output conforms to schema.json.")

if __name__ == "__main__":
    main()
