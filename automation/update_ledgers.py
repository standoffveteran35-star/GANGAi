import os
import json
import datetime
import re
import argparse

# Path configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")
USER_PATH = os.path.join(KNOWLEDGE_DIR, "user.md")
PROJECTS_PATH = os.path.join(KNOWLEDGE_DIR, "projects.md")
DECISIONS_PATH = os.path.join(KNOWLEDGE_DIR, "DECISIONS.md")
LESSONS_PATH = os.path.join(KNOWLEDGE_DIR, "LESSONS.md")
MEMORY_PATH = os.path.join(KNOWLEDGE_DIR, "Memory.md")

def load_json_data(filepath_or_string):
    """
    Loads JSON data from a file path or a raw JSON string.
    """
    if os.path.exists(filepath_or_string):
        with open(filepath_or_string, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(filepath_or_string)

def insert_after_heading(file_path, heading, text_to_insert):
    """
    Inserts a text block directly after a specified heading in a markdown file.
    """
    if not os.path.exists(file_path):
        print(f"[-] File not found: {file_path}")
        return False
        
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    inserted = False
    new_lines = []
    for line in lines:
        new_lines.append(line)
        if not inserted and heading in line:
            new_lines.append("\n" + text_to_insert + "\n")
            inserted = True
            
    if not inserted:
        new_lines.append("\n" + text_to_insert + "\n")
        
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    return True

def classify_lesson_heading(lesson_text):
    """
    Heuristically matches a lesson to the correct header category in LESSONS.md.
    """
    text = lesson_text.lower()
    if any(w in text for w in ["academic", "curriculum", "student", "teacher", "teaching", "syllabus", "exam", "coaching", "school"]):
        return "## 1. Academic & Education Systems"
    elif any(w in text for w in ["business", "operations", "process", "scale", "team", "founder", "delegation"]):
        return "## 2. Business Operations & Scale"
    elif any(w in text for w in ["marketing", "advertising", "conversion", "leads", "workshop", "acquisition", "flyers", "sales"]):
        return "## 3. Marketing & Student Acquisition"
    elif any(w in text for w in ["ai", "automation", "scripts", "sheets", "supabase", "netlify", "manychat", "code"]):
        return "## 4. AI & Automation Systems"
    return "## 1. Academic & Education Systems" # Default fallback

def apply_decision_updates(updates):
    """
    Appends new decisions under '## Active Decision Ledger' in DECISIONS.md.
    """
    if not updates:
        return
        
    today = datetime.date.today().strftime("%Y-%m-%d")
    review_date = (datetime.date.today() + datetime.timedelta(days=90)).strftime("%Y-%m-%d")
    
    decisions_block = ""
    for update in updates:
        decision = update.get("decision")
        reasoning = update.get("reasoning", "Not specified")
        
        title = decision[:45] + "..." if len(decision) > 45 else decision
        
        decisions_block += f"### {today} | {title}\n"
        decisions_block += f"* **Decision:** {decision}\n"
        decisions_block += f"* **Reasoning:** {reasoning}\n"
        decisions_block += f"* **Expected Outcome:** Pending\n"
        decisions_block += f"* **Review Date:** {review_date}\n"
        decisions_block += f"* **Actual Outcome:** Pending\n"
        decisions_block += f"* **Lesson:** Pending\n\n"
        
    if decisions_block:
        insert_after_heading(DECISIONS_PATH, "## Active Decision Ledger", decisions_block.strip())
        print(f"[+] Integrated {len(updates)} decision(s) into DECISIONS.md.")

def apply_lesson_updates(updates):
    """
    Classifies and appends new lessons into LESSONS.md.
    """
    if not updates:
        return
        
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    # Group lessons by their heading category
    grouped_lessons = {}
    for update in updates:
        lesson = update.get("lesson")
        evidence = update.get("evidence", "Observed in latest session.")
        confidence = update.get("confidence", 0.9)
        
        confidence_str = "Critical / Absolute" if confidence >= 0.99 else ("High" if confidence >= 0.8 else "Medium")
        
        lesson_md = f"* **Lesson:** {lesson}\n"
        lesson_md += f"  * **Evidence:** {evidence}\n"
        lesson_md += f"  * **Confidence:** {confidence_str}\n"
        lesson_md += f"  * **Last Confirmed:** {today}\n"
        
        heading = classify_lesson_heading(lesson)
        if heading not in grouped_lessons:
            grouped_lessons[heading] = []
        grouped_lessons[heading].append(lesson_md)
        
    for heading, lessons in grouped_lessons.items():
        lessons_block = "\n".join(lessons)
        insert_after_heading(LESSONS_PATH, heading, lessons_block)
        print(f"[+] Integrated {len(lessons)} lesson(s) under '{heading}' in LESSONS.md.")

def apply_memory_updates(updates):
    """
    Appends new timeline/memory events under the current year in Memory.md.
    """
    if not updates:
        return
        
    current_year = datetime.date.today().strftime("%Y")
    month_name = datetime.date.today().strftime("%B")
    
    events_block = ""
    for update in updates:
        event = update.get("event")
        importance = update.get("importance", "medium")
        events_block += f"* **{month_name}:** {event} (Importance: {importance})\n"
        
    if events_block:
        # Look for the year heading like "### 2026"
        year_heading = f"### {current_year}"
        insert_after_heading(MEMORY_PATH, year_heading, events_block.strip())
        print(f"[+] Integrated {len(updates)} timeline event(s) into Memory.md.")

def apply_project_updates(updates):
    """
    Integrates project updates (add/update/pause/complete) into projects.md.
    """
    if not updates:
        return
        
    with open(PROJECTS_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        
    for update in updates:
        action = update.get("action")
        project_name = update.get("project_name")
        details = update.get("details", "")
        
        # Simple Add logic
        if action == "add":
            project_md = f"#### Project: {project_name}\n"
            project_md += f"* **Status:** Active\n"
            project_md += f"* **Current Stage:** Concept\n"
            project_md += f"* **Goal:** {details}\n"
            project_md += f"* **Next Milestone:** Define milestones\n"
            project_md += f"* **Owner:** Pavan\n"
            
            insert_after_heading(PROJECTS_PATH, "## Active Projects", project_md)
            print(f"[+] Added new project '{project_name}' to projects.md.")
            
        elif action in ["pause", "complete"]:
            # Logic to search and modify status/category in markdown file
            pattern = rf"(#### Project: {re.escape(project_name)}.*?)(?=#### Project:|---|$)"
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                project_block = match.group(1)
                # Remove from current location
                content = content.replace(project_block, "")
                
                # Format moving details
                new_status = "Paused" if action == "pause" else "Completed"
                updated_block = re.sub(r"\* \*\*Status:\*\* \w+", f"* **Status:** {new_status}", project_block)
                
                if action == "complete":
                    today = datetime.date.today().strftime("%Y-%m-%d")
                    # Swap template metrics
                    updated_block = re.sub(r"\* \*\*Current Stage:\*\*.*", f"* **Completion Date:** {today}", updated_block)
                
                # Append to corresponding section
                heading = "## Paused Projects" if action == "pause" else "## Completed Projects"
                insert_heading_pattern = rf"({re.escape(heading)}.*?\n)"
                content = re.sub(insert_heading_pattern, rf"\1\n{updated_block.strip()}\n\n", content)
                
                with open(PROJECTS_PATH, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"[+] Moved project '{project_name}' to {new_status} Projects.")
            else:
                print(f"[-] Could not find project '{project_name}' to update status.")

def main():
    parser = argparse.ArgumentParser(description="Update PersonalOS markdown ledgers with structured JSON updates.")
    parser.add_argument("input", help="Path to JSON file or raw JSON string containing updates.")
    args = parser.parse_args()
    
    try:
        data = load_json_data(args.input)
        print("[+] Parsed updates payload successfully.")
        
        apply_decision_updates(data.get("decision_updates"))
        apply_lesson_updates(data.get("lesson_updates"))
        apply_memory_updates(data.get("memory_updates"))
        apply_project_updates(data.get("project_updates"))
        
        print("[+] Ledger sync complete.")
    except Exception as e:
        print(f"[-] Failed to apply updates: {e}")

if __name__ == "__main__":
    main()
