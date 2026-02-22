import edge_tts
import os
import math
from mutagen.mp3 import MP3
from core.db_manager import DBManager

class VoiceEngine:
    def __init__(self):
        self.db = DBManager()
        
        # 🟢 UPGRADED: Expanded voice map for all 17 dynamic niches
        self.voice_map = {
            # Energetic & Authoritative
            "motivation": "en-US-ChristopherNeural",
            "sports": "en-US-EricNeural",
            "gaming": "en-US-SteffanNeural",
            "entertainment": "en-US-MichelleNeural",
            
            # Documentary & Professional (British/Refined)
            "space": "en-GB-RyanNeural",
            "history": "en-GB-SoniaNeural",
            "prehistoric": "en-GB-ThomasNeural",
            "truecrime": "en-US-AriaNeural",  # Serious, slightly darker tone
            
            # Calming & Engaging
            "nature": "en-US-JennyNeural",
            "animals": "en-US-AnaNeural",
            "family": "en-US-AmberNeural",
            "diy": "en-US-RogerNeural",
            
            # News & Informative
            "worldnews": "en-US-GuyNeural",
            "finance": "en-US-JasonNeural",
            "science": "en-US-BrianNeural",
            "health": "en-US-JaneNeural",
            "movies": "en-US-TonyNeural",
            "travel": "en-AU-NatashaNeural", # Australian accent for travel
            
            # Fallback
            "general": "en-US-GuyNeural"
        }

    async def generate_audio(self):
        task = self.db.collection.find_one({"status": "scripted"})
        if not task:
            return

        folder = task.get("folder_path")
        scenes = task.get("script_data", [])
        niche = task.get("niche", "general").lower()

        # Determine the best voice for this video's emotional tone
        selected_voice = self.voice_map.get(niche, "en-US-GuyNeural")

        print(f"🎙️ Generating Audio ({len(scenes)} segments) using {selected_voice} for niche '{niche}'...")

        updated_scenes = []
        for i, scene in enumerate(scenes):
            filename = f"voice_{i}.mp3"
            path = os.path.join(folder, filename)
            text = scene["text"]

            try:
                # 🟢 Apply the dynamically selected voice
                communicate = edge_tts.Communicate(text, selected_voice, rate="+10%")
                await communicate.save(path)

                duration = MP3(path).info.length

                scene["audio_path"] = path
                scene["duration"] = duration

                required_images = math.ceil(duration / 4.0)
                scene["image_count"] = max(1, int(required_images))
                img_duration = duration / scene["image_count"]

                updated_scenes.append(scene)
                print(
                    f"   Seg {i+1}: {duration:.1f}s -> {scene['image_count']} visuals (~{img_duration:.1f}s each)"
                )

            except Exception as e:
                print(f"   ❌ Failed scene {i}: {e}")

        self.db.collection.update_one(
            {"_id": task["_id"]},
            {"$set": {"script_data": updated_scenes, "status": "voiced"}},
        )
        print("✅ Audio Generation Complete.")