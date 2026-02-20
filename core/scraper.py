import requests
import feedparser
import random
import datetime
import re
import os
from groq import Groq  # <--- CHANGED
from core.db_manager import DBManager
from dotenv import load_dotenv
from core.db_manager import DBManager


class NewsScraper:
    def __init__(self):
        self.db = DBManager()
        # Initialize Groq Client
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))  # <--- CHANGED
        self.model = "llama-3.3-70b-versatile"  # Fast and free on Groq
        self.headers = {"User-Agent": "Mozilla/5.0"}

        self.niche_map = {
            "morning": {
                "niche": "motivation",
                "sources": [
                    "https://tinybuddha.com/feed/",
                    "https://dailystoic.com/feed/",
                    "https://zenhabits.net/feed/",
                    "https://www.marcandangel.com/feed/",
                    "https://www.pickthebrain.com/blog/feed/",
                ],
            },
            "noon": {
                "niche": "space",
                "sources": [
                    "https://www.space.com/feeds/news",
                    "https://www.sciencedaily.com/rss/space_time.xml",
                    "https://www.nasa.gov/rss/dyn/breaking_news.rss",
                    "https://universetoday.com/feed",
                ],
            },
            "evening": {
                "niche": "nature",
                "sources": [
                    "https://www.sciencedaily.com/rss/fossils_ruins/paleontology.xml",
                    "https://www.sciencedaily.com/rss/plants_animals/endangered_animals.xml",
                    "https://news.mongabay.com/feed/",
                    "https://www.smithsonianmag.com/rss/science-nature/",
                    "https://www.earth.com/feed/",
                    "https://phys.org/rss-feed/biology-news/ecology/",
                ],
            },
            "night": {
                "niche": "history",
                "sources": [
                    "https://www.historytoday.com/feed/rss.xml",
                    "https://www.historynet.com/feed",
                    "https://www.ancient-origins.net/rss.xml",
                    "https://www.archaeology.org/news?format=feed",
                    "http://feeds.feedburner.com/HeritageDaily",
                ],
            },
        }

    def get_time_slot(self):
        h = datetime.datetime.now().hour
        if 5 <= h < 12:
            return "morning"
        elif 12 <= h < 17:
            return "noon"
        elif 17 <= h < 21:
            return "evening"
        else:
            return "night"

    def fetch_rss(self, url):
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            if r.status_code == 200:
                return feedparser.parse(r.content).entries[
                    :10
                ]  # increased to 10 for more variety
        except:
            pass
        return []

    # 🟢 NEW: AI VIRAL JUDGE
    def pick_viral_topic(self, candidates, niche):
        """
        Uses Groq (Cloud AI) to analyze titles and pick the most click-worthy one.
        """
        titles = [f"{i}. {c['title']}" for i, c in enumerate(candidates)]
        titles_text = "\n".join(titles)

        prompt = f"""
        TASK: You are a YouTube Viral Content Strategist.
        GOAL: Pick the ONE headline from the list below that has the highest potential to go VIRAL as a YouTube Short.
        NICHE: {niche}
        
        CRITERIA:
        1. Look for shock value, curiosity gaps, or major breakthroughs.
        2. Avoid boring, generic, or corporate announcements.
        
        HEADLINES:
        {titles_text}
        
        OUTPUT FORMAT: Return ONLY the index number (integer) of the best headline. Example: 5
        """

        try:
            print(
                f"   🤖 Groq Judge: Analyzing {len(candidates)} headlines for virality..."
            )

            # CALL GROQ API INSTEAD OF OLLAMA
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
            )

            content = chat_completion.choices[0].message.content.strip()
            match = re.search(r"\d+", content)

            if match:
                index = int(match.group())
                if 0 <= index < len(candidates):
                    print(
                        f"      🏆 AI Selected: '{candidates[index]['title'][:40]}...'"
                    )
                    return candidates[index]

            print("      ⚠️ AI failed to return a valid number. Picking random.")
            return random.choice(candidates)

        except Exception as e:
            print(f"      ❌ Groq Error: {e}. Fallback to random.")
            return random.choice(candidates)

    # 🟢 NEW: Request Top 3 indices from the AI
    def pick_top_3_viral_topics(self, candidates, niche):
        """
        Uses Groq (Cloud AI) to analyze titles and pick the TOP 3 click-worthy ones.
        """
        titles = [f"{i}. {c['title']}" for i, c in enumerate(candidates)]
        titles_text = "\n".join(titles)

        prompt = f"""
        TASK: You are a YouTube Viral Content Strategist.
        GOAL: Pick the THREE best headlines from the list below that have the highest potential to go VIRAL as YouTube Shorts.
        NICHE: {niche}
        
        CRITERIA:
        1. Look for shock value, curiosity gaps, or major breakthroughs.
        2. Avoid boring, generic, or corporate announcements.
        
        HEADLINES:
        {titles_text}
        
        OUTPUT FORMAT: Return ONLY a JSON dictionary with a key "indices" containing an array of exactly 3 integer indices of the best headlines. 
        Example: {{"indices": [5, 12, 2]}}
        """

        try:
            print(
                f"   🤖 Groq Judge: Analyzing {len(candidates)} headlines for the Top 3..."
            )

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

            content = chat_completion.choices[0].message.content.strip()

            import json

            response_data = json.loads(content)
            indices = response_data.get("indices", [])

            top_3_candidates = []
            for index in indices[:3]:
                if isinstance(index, int) and 0 <= index < len(candidates):
                    top_3_candidates.append(candidates[index])

            print(f"      🏆 AI Selected 3 Potential Winners.")
            return top_3_candidates

        except Exception as e:
            print(f"      ❌ Groq Error: {e}. Fallback to random 3.")
            import random

            return random.sample(candidates, min(3, len(candidates)))

    # 🟢 NEW: Manual Input AI Refinement
    def refine_user_idea(self, topic, content, feedback=""):
        prompt = f"""
        TASK: You are a YouTube Viral Content Strategist.
        The user has provided a raw idea for a video. Refine it into a highly engaging, viral-ready story summary (about 3-5 sentences) that can be easily turned into a script.
        
        RAW TOPIC: {topic}
        RAW CONTENT: {content}
        USER FEEDBACK ON PREVIOUS ATTEMPT (if any): {feedback}
        
        CRITERIA:
        1. Make it sound dramatic, interesting, and tailored for YouTube Shorts.
        2. Do NOT write the actual script scenes yet (the Brain module will do that later).
        3. Return ONLY the refined summary. No conversational filler.
        """

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ AI Refinement Error: {e}")
            return content

    # 🟢 OPTIMIZED: The 4-Attempt Loop with Top 3 Batch Checking
    def scrape_targeted_niche(self, forced_slot=None):
        slot = forced_slot if forced_slot else self.get_time_slot()
        config = self.niche_map.get(slot, self.niche_map["noon"])
        niche = config["niche"]

        print(f"🕵️‍♂️ Strategy: {slot.upper()} ({niche})")

        # Step 1: Gather raw candidates without checking the DB yet!
        candidates = []
        for url in config["sources"]:
            entries = self.fetch_rss(url)
            for e in entries:
                if hasattr(e, "title"):
                    candidates.append(
                        {
                            "title": e.title,
                            "summary": getattr(e, "summary", e.title)[:3000],
                            "link": getattr(e, "link", ""),
                            "niche": niche,
                        }
                    )

        if not candidates:
            print("❌ No articles found in RSS feeds. Try a different slot.")
            return

        # Step 2: The Optimized Retry Loop
        attempts = 0
        max_tries = 4

        while attempts < max_tries and len(candidates) >= 3:
            print(f"   🔄 Attempt {attempts + 1}/{max_tries} (Batch of 3)...")

            # Ask AI for Top 3
            top_3 = self.pick_top_3_viral_topics(candidates, niche)

            # Step 3: Check these 3 against the database
            unique_winners = []
            for candidate in top_3:
                # 🟢 DB CONNECTION SAVER: We only query the DB 3 times per loop, not 50+ times!
                is_duplicate = self.db.task_exists(
                    candidate["title"], candidate["link"]
                )
                if not is_duplicate:
                    unique_winners.append(candidate)

                # Remove from the raw candidate pool so AI doesn't pick it again next loop
                if candidate in candidates:
                    candidates.remove(candidate)

            # Step 4: Process the winners
            if unique_winners:
                # If multiple are unique, pick one randomly as requested
                import random

                final_winner = random.choice(unique_winners)

                print(
                    f"      🎉 Unique Topic Secured: '{final_winner['title'][:40]}...'"
                )

                self.db.add_task(
                    final_winner["title"],
                    final_winner["summary"],
                    f"{niche.upper()}",
                    "pending",
                    {
                        "niche": niche,
                        "niche_slot": slot,
                        "source_url": final_winner["link"],
                    },
                )
                return
            else:
                print(
                    "      ⚠️ All 3 AI choices were DB duplicates. Retrying with remaining pool..."
                )

            attempts += 1

        print("❌ Exceeded max retries. Could not find a unique viral topic today.")
