import json
import re
import os
from groq import Groq
from core.db_manager import DBManager
from dotenv import load_dotenv

load_dotenv()


class ScriptGenerator:
    def __init__(self):
        self.db = DBManager()
        # Initialize Groq Client
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"  # Fast, high quality

    def repair_json(self, json_str):
        try:
            # Clean generic AI chatter
            json_str = re.sub(r"^[^{]*", "", json_str)
            json_str = re.sub(r"[^}]*$", "", json_str)
            return json.loads(json_str)
        except:
            return None

    def generate_script(self):
        task = self.db.collection.find_one({"status": "pending"})
        if not task:
            print("📭 No pending tasks.")
            return

        niche = task.get("niche", "tech")
        source = task.get("content", "")[:3000]
        source_url = task.get("source_url", "https://news.google.com")

        # 🟢 UPGRADED PROMPT: SEO, Looping, Authenticity, and Advanced CTAs
        prompt = f"""
            ROLE: Documentary Director and YouTube SEO Expert.
            TASK: Convert this news into a structured video script and optimize its discoverability.
            SOURCE: "{source}"
            
            REQUIREMENTS:
            1. **TONE & AUTHENTICITY**: Write the script using a conversational, 'creator' mindset. Use words like "I" and "We" to make it feel like a human is talking to a friend, rather than a robot reading a Wikipedia page.
            2. Break the story into 6-8 distinct SCENES.
            3. 'text': The narration for that scene (1-2 sentences).
            
            4. **VISUALS**:
                - 'keywords': List exactly 2 specific search terms for stock footage.
                - 'image_count': 1 (slow paced) or 2 (fast paced).
            
            5.  **METADATA & SEO (CRITICAL)**:
                - 'title': MUST be "Clickbait" style. High curiosity. Max 50 chars.
                - 'description': 3-sentence summary + call to action.
                - 'hashtags': MUST include #Shorts #Viral + AT LEAST 10 to 15 highly specific, SEO-optimized hashtags relevant to the story to maximize algorithmic reach. (e.g., #SpaceX #Astronomy #UniverseFacts).
                - 'tags': A comma-separated list of 15 to 20 strong, highly searched SEO keywords for the YouTube backend tags box.
                
            6. **CRITICAL - KEYWORD RULES (ZERO TOLERANCE)**:
                - 'keywords': A list of exactly 2 string search terms.
                - **NEVER leave this empty.**
                - **SPECIFICITY**: Use specific names (e.g., "Sony Camera", "Elon Musk").
            
            7. **CRITICAL - CTA & OUTRO RULES**: 
                - The FINAL SCENE must drive a specific, high-value algorithmic action (Share, Save, or Comment).
                - DO NOT ask for likes or subscribes. 
                - Example for Comments: "What do you think about this? Let me know below!"
                - Example for Shares/Saves: "Send this to someone who needs to hear it," or "Save this for the next time you..."
                - **VISUALS FOR CTA**: Do NOT use boring keywords like "laptop", "phone", or "green screen". Keep the visuals EPIC and tied to the {niche}. (e.g., if space, use ["Cinematic Galaxy", "Supernova"]. If motivation, use ["Man reaching summit", "Victory"]).
            
            8. **NARRATION ('text') & LOOPING MECHANIC**:
                - Scene 1 MUST be a fast, high-energy "Hook" starting immediately with the core value.
                - **CRITICAL**: DO NOT always use "Stop scrolling". Be creative!
                - **LOOPING MECHANIC (CRITICAL)**: The very last sentence of the script (in the final scene) MUST be written so that it seamlessly flows right back into the first sentence of the hook, creating an infinite loop. 
                - Example: If the hook starts with "Scientists just found a new planet," the outro should end with "And that is exactly why..."
            
            OUTPUT FORMAT (JSON ONLY):
            {{
                "title": "Viral Title Here",
                "description": "Short summary...",
                "hashtags": "#Tag1 #Tag2 #Tag3...",
                "tags": "keyword1, keyword2, long tail keyword 3...",
                "scenes": [
                    {{
                        "text": "Scientists have made a discovery.",
                        "keywords": ["Scientist", "Lab"],
                        "image_count": 1
                    }}
                ]
            }}
        """

        try:
            print(f"🧠 Groq Director: Segmenting {niche.upper()} story...")

            # CALL GROQ API
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that outputs ONLY valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
                response_format={"type": "json_object"},
            )

            response_content = chat_completion.choices[0].message.content
            data = self.repair_json(response_content)

            if not data or "scenes" not in data:
                raise ValueError("Invalid JSON structure from AI")

            # 🟢 Create Metadata File
            meta_filename = f"metadata_{task['_id']}.txt"
            metadata_content = f"""
===================================================
🚀 YOUTUBE UPLOAD METADATA
===================================================
📌 TITLE: {data.get('title')}
📝 DESCRIPTION: {data.get('description')}
👇 Read the full story here: {source_url}
---------------------------------------------------
🔥 HASHTAGS: {data.get('hashtags')}
🏷️ TAGS: {data.get('tags')}
---------------------------------------------------
"""
            with open(meta_filename, "w", encoding="utf-8") as f:
                f.write(metadata_content)

            # Update Database
            self.db.collection.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "script_data": data["scenes"],
                        "title": data.get("title", task["title"]),
                        "ai_description": data.get("description"),
                        "ai_hashtags": data.get("hashtags"),
                        "ai_tags": data.get("tags"),
                        "status": "scripted",
                    }
                },
            )
            print(
                f"✅ Script Segmented: {len(data['scenes'])} scenes created with SEO and Looping mechanics."
            )

        except Exception as e:
            print(f"❌ Brain Error: {e}")
