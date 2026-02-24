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
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"

    def repair_json(self, json_str):
        try:
            json_str = re.sub(r"^[^{]*", "", json_str)
            json_str = re.sub(r"[^}]*$", "", json_str)
            return json.loads(json_str)
        except:
            return None

    def generate_meta_prompt(self, niche, source_text):
        """
        The Meta-Prompt: AI generates the persona and visual rules BEFORE writing the script.
        """
        print(f"🕵️‍♂️ AI Strategist: Analyzing '{niche}' news to build custom persona...")

        meta_prompt = f"""
        TASK: You are a Master YouTube Shorts Strategist. 
        I am going to give you a raw news story about {niche}.
        You need to invent a highly specific, engaging Persona/Role for the scriptwriter, and generate a pool of 10 aesthetic visual search terms for the video editor.
        
        NEWS STORY: "{source_text[:1500]}"
        
        REQUIREMENTS:
        1. 'system_prompt': Write a 3-sentence persona. Make it perfectly match the mood of the news.
        2. 'visual_keywords': Provide exactly 10 highly cinematic, specific stock video search terms. Do NOT use generic words.
        
        OUTPUT ONLY JSON:
        {{
            "system_prompt": "Your custom persona here...",
            "visual_keywords": ["keyword 1", "keyword 2", "keyword 3"]
        }}
        """

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": meta_prompt}],
                model=self.model,
                response_format={"type": "json_object"},
            )
            return self.repair_json(chat_completion.choices[0].message.content)
        except Exception as e:
            print(f"❌ Meta-Prompting Error: {e}")
            return {
                "system_prompt": "You are a highly energetic YouTube Shorts creator.",
                "visual_keywords": ["Cinematic", "Epic", "Abstract"],
            }

    def generate_script(self):
        task = self.db.collection.find_one({"status": "pending"})
        if not task:
            print("📭 No pending tasks.")
            return

        niche = task.get("niche", "general")
        source = task.get("content", "")[:3000]
        source_url = task.get("source_url", "https://news.google.com")

        meta_data = self.generate_meta_prompt(niche, source)
        sys_prompt = meta_data.get("system_prompt", "You are a Viral Content Creator.")
        visual_kw_list = meta_data.get(
            "visual_keywords", ["Cinematic", "Epic", "Abstract"]
        )
        pre_hashtags = task.get("predefined_hashtags", "#Shorts #Viral")

        prompt = f"""
            ROLE: {sys_prompt}
            TASK: Convert this news into a structured video script and optimize its discoverability. Convert this news into a short, punchy video script between 50 seconds minimum and 65 seconds maximum.
            SOURCE: "{source}"
            
            REQUIREMENTS:
            1. **TONE & AUTHENTICITY (CRITICAL FOR VOICEOVER)**: Follow your assigned ROLE strictly. You are writing a script that will be read by an AI voice. 
                - You MUST use heavy punctuation. Use commas (,), ellipses (...), question marks (?), and em-dashes (—) to force the voice engine to pause, breathe, and sound human.
                - Write the way people actually speak.
            2. Break the story between 4-6 distinct SCENES. Each scene must be 7 to 8 seconds.
            3. 'text': The narration for that scene.
            
            4. **VISUALS & B-ROLL (DYNAMIC PACING & NO DUPLICATES)**:
                - You must act as a Video Editor and pace the visuals based on the length of the scene's 'text':
                    - SHORT scene (under 10 words): Provide EXACTLY 1 search phrase and set 'image_count': 1.
                    - MODERATE scene (10-18 words): Provide EXACTLY 2 search phrases and set 'image_count': 2.
                    - LONG scene (18+ words): Provide EXACTLY 3 search phrases and set 'image_count': 3.
                - **INSPIRATION BOARD**: {visual_kw_list}. Use these aesthetic themes as a guide, but THINK FOR YOURSELF to match the narration. Add unique modifiers.
                - **CRITICAL - NO DUPLICATES**: NEVER repeat a search phrase. Every phrase in the script must be 100% unique.
            
            5.  **METADATA & SEO**:
                - 'title': MUST be "Clickbait" style. High curiosity. Max 50 chars.
                - 'description': 3-sentence summary + call to action.
                - 'hashtags': Use these exactly: {pre_hashtags}, and add 5 more specific ones.
                - 'tags': An array of 10-15 highly searched SEO keywords.
            
            6. **CRITICAL - CTA & OUTRO RULES**: 
                - The FINAL SCENE must drive an explicit call to action. 
                - You MUST end the entire script with the exact phrase: "Please like, share, and subscribe!"
            
            7. **NARRATION**:
                - Scene 1 MUST be a fast, high-energy "Hook".
                - Because the video ends with a standard CTA, do not attempt to loop the script. End the video naturally after asking them to subscribe.
            
            OUTPUT FORMAT (JSON ONLY):
            {{
                "title": "Viral Title Here",
                "description": "Short summary...",
                "hashtags": "#Tag1 #Tag2...",
                "tags": ["keyword1", "keyword2", "keyword3"],
                "scenes": [
                    {{
                        "text": "Your narration here...",
                        "keywords": ["Dynamic phrase 1", "Dynamic phrase 2"],
                        "image_count": 2
                    }}
                ]
            }}
        """

        try:
            print(f"🧠 Groq Director: Segmenting {niche.upper()} story...")
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You output ONLY valid JSON dictionaries.",
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

            meta_filename = f"metadata_{task['_id']}.txt"
            with open(meta_filename, "w", encoding="utf-8") as f:
                f.write(f"TITLE: {data.get('title')}\nHASHTAGS: {data.get('hashtags')}")

            # 🟢 FIX: Safely join the tags array back into a comma-separated string for YouTube
            raw_tags = data.get("tags", [])
            formatted_tags = (
                ", ".join(raw_tags) if isinstance(raw_tags, list) else str(raw_tags)
            )

            self.db.collection.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "script_data": data["scenes"],
                        "title": data.get("title", task["title"]),
                        "ai_description": data.get("description"),
                        "ai_hashtags": data.get("hashtags"),
                        "ai_tags": formatted_tags,
                        "status": "scripted",
                    }
                },
            )
            print("✅ Script Segmented! AI generated unique search arrays for visuals.")
        except Exception as e:
            print(f"❌ Brain Error: {e}")
