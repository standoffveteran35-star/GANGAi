import os
import json
import argparse
import sys
from dotenv import load_dotenv
import requests

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

# Import ledger update functions from update_ledgers.py
sys.path.append(os.path.join(BASE_DIR, "automation"))
try:
    import update_ledgers
except ImportError:
    # Fallback to absolute import paths if necessary
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import update_ledgers

def extract_with_gemini(conversation_text):
    """
    Extracts structured updates using Gemini-2.5-flash.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[-] Error: GEMINI_API_KEY is not configured in your .env file.")
        return None

    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        # Strip metadata keys that the google-genai SDK's schema validator rejects
        gemini_schema = SCHEMA.copy()
        gemini_schema.pop("$schema", None)
        gemini_schema.pop("title", None)
        
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=gemini_schema,
            temperature=0.1
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=conversation_text,
            config=config
        )
        
        return json.loads(response.text)
    except Exception as e:
        print(f"[-] Gemini extraction failed: {e}")
        return None

def extract_with_openai(conversation_text):
    """
    Extracts structured updates using OpenAI GPT-4o-mini.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[-] Error: OPENAI_API_KEY is not configured in your .env file.")
        return None

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"{SYSTEM_PROMPT}\n\nConversation to analyze:\n{conversation_text}"
        
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
            timeout=40
        )
        response.raise_for_status()
        res_json = response.json()
        raw_content = res_json["choices"][0]["message"]["content"]
        
        return json.loads(raw_content)
    except Exception as e:
        if "429" in str(e):
            print("[-] OpenAI GPT extraction failed: Quota Exceeded (429 Rate Limit). Please verify your billing balance.")
        else:
            print(f"[-] OpenAI GPT extraction failed: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Extract updates from a chat log and merge them directly to PersonalOS ledgers.")
    parser.add_argument("file", nargs="?", help="Path to the conversation log file. If omitted, reads from stdin.")
    parser.add_argument("--model", choices=["gemini", "gpt"], default="gemini", help="The LLM backend to run extraction (default: gemini).")
    args = parser.parse_args()
    
    # Read conversation text
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                conversation_text = f.read()
        except Exception as e:
            print(f"[-] Error reading file: {e}")
            sys.exit(1)
    else:
        print("[*] Reading conversation from stdin (Press Ctrl+Z/Ctrl+D to finalize)...")
        conversation_text = sys.stdin.read()
        
    if not conversation_text.strip():
        print("[-] Error: Empty conversation input.")
        sys.exit(1)
        
    print(f"[*] Analyzing conversation using {args.model.upper()}...")
    
    if args.model == "gemini":
        extracted_data = extract_with_gemini(conversation_text)
    else:
        extracted_data = extract_with_openai(conversation_text)
        
    if not extracted_data:
        print("[-] Extraction failed. Ledger files were not modified.")
        sys.exit(1)
        
    # Validate against schema
    errors = update_ledgers.validate_against_schema(extracted_data)
    if errors:
        print("[-] Extracted JSON failed schema validation:")
        for err in errors:
            print(f"  * {err}")
        sys.exit(1)
        
    print("[+] Extraction successful and schema-validated.")
    print("Updates to apply:")
    print(json.dumps(extracted_data, indent=2))
    
    # Apply updates
    print("\n[*] Applying updates to ledgers...")
    update_ledgers.apply_decision_updates(extracted_data.get("decision_updates"))
    update_ledgers.apply_lesson_updates(extracted_data.get("lesson_updates"))
    update_ledgers.apply_memory_updates(extracted_data.get("memory_updates"))
    update_ledgers.apply_project_updates(extracted_data.get("project_updates"))
    
    print("[+] Ledger sync complete!")

if __name__ == "__main__":
    main()
