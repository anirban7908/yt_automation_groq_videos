import requests
import feedparser
import random
import datetime
import re
import os
from groq import Groq
from core.db_manager import DBManager
from dotenv import load_dotenv


class NewsScraper:
    def __init__(self):
        self.db = DBManager()
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"
        self.MASTER_NICHES = {
            "entertainment": [
                "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml",
                "https://www.eonline.com/syndication/feeds/rssfeeds/topstories.xml",
                "https://www.hollywoodreporter.com/feed/",
                "https://www.tmz.com/rss.xml",
            ],
            "gaming": [
                "https://feeds.ign.com/ign/all",
                "https://www.polygon.com/rss/index.xml",
                "https://kotaku.com/rss",
                "https://www.pcgamer.com/rss/",
            ],
            "sports": [
                "https://www.espn.com/espn/rss/news",
                "https://api.foxsports.com/v2/content/optimized-rss?partnerKey=MB0Wehpmuj2lUhuRhQaafhBjAJqaPU244mlTDK1i&size=30&tags=fs/mlb",
                "https://www.cbssports.com/rss/headlines/",
                "https://sports.yahoo.com/rss/",
            ],
            "animals": [
                "https://www.sciencedaily.com/rss/plants_animals/dogs.xml",
                "https://www.nationalgeographic.com/animals/rss",
                "https://news.mongabay.com/feed/",
                "https://www.treehugger.com/feed",
            ],
            "movies": [
                "https://variety.com/feed/",
                "https://screenrant.com/feed/",
                "https://www.indiewire.com/feed/",
                "https://www.cinemablend.com/rss",
            ],
            "science": [
                "https://www.theverge.com/rss/index.xml",
                "https://techcrunch.com/feed/",
                "https://www.livescience.com/home/feed/about.xml",
                "https://phys.org/rss-feed/",
            ],
            "worldnews": [
                "http://feeds.bbci.co.uk/news/world/rss.xml",
                "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
                "https://www.aljazeera.com/xml/rss/all.xml",
                "https://feeds.npr.org/1004/rss.xml",
            ],
            "finance": [
                "https://search.cnbc.com/rs/search/combinedcms/view.xml?id=10000664",
                "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
                "https://finance.yahoo.com/news/rssindex",
                "http://feeds.marketwatch.com/marketwatch/topstories/",
            ],
            "health": [
                "https://www.sciencedaily.com/rss/health_medicine/fitness.xml",
                "https://www.health.harvard.edu/blog/feed",
                "https://rssfeeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC",
                "https://newsnetwork.mayoclinic.org/feed/",
            ],
            "travel": [
                "https://www.cntraveler.com/feed/rss",
                "https://www.lonelyplanet.com/articles/feed",
                "https://thepointsguy.com/feed/",
                "https://www.nomadicmatt.com/travel-blogs/feed/",
            ],
            "truecrime": [
                "https://www.oxygen.com/crime-news/feed",
                "https://www.cbsnews.com/latest/rss/48hours",
                "https://www.crimeonline.com/feed/",
                "https://www.fbi.gov/feeds/national-press-releases/rss.xml",
            ],
            "history": [
                "https://www.history.com/.rss/excerpt/news",
                "https://www.smithsonianmag.com/rss/history/",
                "https://www.ancient-origins.net/rss.xml",
                "https://www.archaeology.org/news?format=feed",
            ],
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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            print(f"      🔗 Fetching: {url}")
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                entries = feedparser.parse(r.content).entries[:10]
                if entries:
                    print(f"         ✅ Found {len(entries)} articles.")
                    return entries
                else:
                    print("         ⚠️ Feed loaded, but no articles found inside.")
            else:
                print(
                    f"         ⛔ HTTP Error {r.status_code}: Website blocked the request."
                )
        except requests.exceptions.Timeout:
            print("         ⏱️ Connection timed out (took longer than 15s).")
        except Exception as e:
            print(f"         ❌ Request Failed: {e}")
        return []

    # ... (Keep pick_viral_topic, pick_top_3_viral_topics, and refine_user_idea EXACTLY the same as before) ...
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

    # 🟢 NEW: Dynamic Random Niche Engine
    # 🟢 OPTIMIZED: The 4-Attempt Loop with Top 3 Batch Checking (Cleaned Imports)
    def scrape_targeted_niche(self, forced_slot=None):
        slot = forced_slot if forced_slot else self.get_time_slot()

        print(f"🕵️‍♂️ Checking used niches for today...")
        used_niches = self.db.get_used_niches_today()
        all_niches = set(self.MASTER_NICHES.keys())

        # Find which niches haven't been generated today
        available_niches = list(all_niches - used_niches)

        if not available_niches:
            print(
                "❌ All 15 niches have been generated today! Resetting pool to allow duplicates..."
            )
            available_niches = list(all_niches)

        # Select a random unique niche for this run
        selected_niche = random.choice(available_niches)
        sources = self.MASTER_NICHES[selected_niche]

        print(
            f"🎯 Dynamic Strategy Active: Selected '{selected_niche.upper()}' for {slot.upper()} slot."
        )

        # Step 1: Gather raw candidates without checking the DB yet!
        candidates = []
        for url in sources:
            entries = self.fetch_rss(url)
            for e in entries:
                if hasattr(e, "title"):
                    candidates.append(
                        {
                            "title": e.title,
                            "summary": getattr(e, "summary", e.title)[:3000],
                            "link": getattr(e, "link", ""),
                            "niche": selected_niche,
                        }
                    )

        if not candidates:
            print("❌ No articles found in RSS feeds. Scraper will exit.")
            return

        # Step 2: The Optimized Retry Loop
        attempts = 0
        max_tries = 4

        while attempts < max_tries and len(candidates) >= 3:
            print(f"   🔄 Attempt {attempts + 1}/{max_tries} (Batch of 3)...")
            top_3 = self.pick_top_3_viral_topics(candidates, selected_niche)

            unique_winners = []
            for candidate in top_3:
                is_duplicate = self.db.task_exists(
                    candidate["title"], candidate["link"]
                )
                if not is_duplicate:
                    unique_winners.append(candidate)
                if candidate in candidates:
                    candidates.remove(candidate)

            if unique_winners:
                # 🟢 FIX: Removed the 'import random' from here!
                final_winner = random.choice(unique_winners)
                print(
                    f"      🎉 Unique Topic Secured: '{final_winner['title'][:40]}...'"
                )

                self.db.add_task(
                    final_winner["title"],
                    final_winner["summary"],
                    f"{selected_niche.upper()}",
                    "pending",
                    {
                        "niche": selected_niche,
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

        print(
            "❌ Exceeded max retries. Could not find a unique viral topic for this niche."
        )
