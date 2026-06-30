import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(ENV_PATH)

# Path configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTEXT_PATH = os.path.join(BASE_DIR, "generated", "Context.md")

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
VECTOR_STORE_ID = os.getenv("OPENAI_VECTOR_STORE_ID")

def update_env_file(key, value):
    """
    Appends or updates a key-value pair in the local .env file.
    """
    lines = []
    updated = False
    
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            updated = True
            break
            
    if not updated:
        lines.append(f"{key}={value}\n")
        
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"[+] Updated .env with {key}={value}")

def make_openai_request(method, endpoint, json_payload=None, files=None):
    """
    Helper to call the OpenAI API with proper Assistants API version headers.
    """
    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "OpenAI-Beta": "assistants=v2"
    }
    if not files:
        headers["Content-Type"] = "application/json"
        
    url = f"https://api.openai.com/v1/{endpoint}"
    
    if method == "POST":
        res = requests.post(url, headers=headers, json=json_payload, files=files, timeout=30)
    elif method == "DELETE":
        res = requests.delete(url, headers=headers, timeout=30)
    else:
        res = requests.get(url, headers=headers, timeout=30)
        
    res.raise_for_status()
    return res.json()

def main():
    if not OPENAI_KEY or "your_openai" in OPENAI_KEY:
        print("[-] Error: OPENAI_API_KEY is not configured or is invalid in your .env file.")
        return

    if not os.path.exists(CONTEXT_PATH):
        print(f"[-] Error: Context file not found at {CONTEXT_PATH}.")
        return

    global ASSISTANT_ID, VECTOR_STORE_ID

    print("[*] Starting PersonalOS Assistant Sync...")

    # 1. Initialize Vector Store if missing
    if not VECTOR_STORE_ID:
        print("[*] Creating a new Vector Store on OpenAI...")
        payload = {"name": "PersonalOS Vector Store"}
        v_store = make_openai_request("POST", "vector_stores", json_payload=payload)
        VECTOR_STORE_ID = v_store["id"]
        update_env_file("OPENAI_VECTOR_STORE_ID", VECTOR_STORE_ID)
    else:
        print(f"[+] Using existing Vector Store: {VECTOR_STORE_ID}")

    # 2. Initialize Assistant if missing
    if not ASSISTANT_ID:
        print("[*] Creating a new PersonalOS Assistant on OpenAI...")
        payload = {
            "name": "PersonalOS Assistant",
            "instructions": (
                "You are the PersonalOS Assistant for Pavan Mahajan. "
                "Always refer to the uploaded Context.md file inside your vector store resources to "
                "maintain alignment with his priorities, decisions, and constraints."
            ),
            "tools": [{"type": "file_search"}],
            "model": "gpt-4o-mini",
            "tool_resources": {
                "file_search": {
                    "vector_store_ids": [VECTOR_STORE_ID]
                }
            }
        }
        assistant = make_openai_request("POST", "assistants", json_payload=payload)
        ASSISTANT_ID = assistant["id"]
        update_env_file("OPENAI_ASSISTANT_ID", ASSISTANT_ID)
    else:
        print(f"[+] Using existing Assistant: {ASSISTANT_ID}")

    # 3. Clean up old files in Vector Store to prevent duplication
    print("[*] Cleaning up old Context files from Vector Store...")
    try:
        files_in_store = make_openai_request("GET", f"vector_stores/{VECTOR_STORE_ID}/files")
        for file_obj in files_in_store.get("data", []):
            file_id = file_obj["id"]
            # Remove from vector store
            make_openai_request("DELETE", f"vector_stores/{VECTOR_STORE_ID}/files/{file_id}")
            # Delete the file object entirely from OpenAI files
            make_openai_request("DELETE", f"files/{file_id}")
            print(f"[+] Deleted old file {file_id} from OpenAI storage.")
    except Exception as e:
        print(f"[!] Warning during cleanup (this is normal if store is empty): {e}")

    # 4. Upload fresh Context.md
    print("[*] Uploading fresh Context.md to OpenAI...")
    with open(CONTEXT_PATH, "rb") as f:
        files = {
            "purpose": (None, "assistants"),
            "file": ("Context.md", f, "text/markdown")
        }
        uploaded_file = make_openai_request("POST", "files", files=files)
        new_file_id = uploaded_file["id"]
        print(f"[+] Uploaded file successful. File ID: {new_file_id}")

    # 5. Attach new file to Vector Store
    print("[*] Linking new Context.md to Vector Store...")
    payload = {"file_id": new_file_id}
    make_openai_request("POST", f"vector_stores/{VECTOR_STORE_ID}/files", json_payload=payload)
    
    print("\n" + "="*40)
    print("[+] SUCCESS: PersonalOS Assistant is fully synced!")
    print(f"    Assistant ID: {ASSISTANT_ID}")
    print(f"    Vector Store ID: {VECTOR_STORE_ID}")
    print(f"    Uploaded File ID: {new_file_id}")
    print("="*40)
    print("\nChat link:")
    print(f"You can chat with this Assistant via API or OpenAI playground using Assistant ID: {ASSISTANT_ID}")

if __name__ == "__main__":
    main()
