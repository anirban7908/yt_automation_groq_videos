import sys
import asyncio
import argparse
import json
import os
import glob
import datetime
from core.scraper import NewsScraper
from core.brain import ScriptGenerator
from core.voice import VoiceEngine
from core.visuals import VisualScout
from core.assembler import VideoAssembler
from core.upload_prep import UploadManager
from core.uploader import YouTubeUploader
from core.db_manager import DBManager


def run_creation_pipeline(slot_name, is_manual=False):
    print(f"\n🎬 STARTING PRODUCTION PIPELINE: {slot_name.upper()}")

    # 🟢 NEW: Manual Flag Logic vs Automated Scraper
    if is_manual:
        print("---------------------------------------")
        print("🛠️ MANUAL OVERRIDE ENGAGED")
        topic = input("📝 Enter the Topic/Title: ")
        content = input("📄 Enter the Content/Idea: ")

        scraper = NewsScraper()
        db = DBManager()
        feedback = ""
        success = False

        for attempt in range(1, 11):
            print(f"\n🧠 AI is refining your idea (Attempt {attempt}/10)...")
            refined_content = scraper.refine_user_idea(topic, content, feedback)

            print("\n✨ --- REFINED IDEA --- ✨")
            print(refined_content)
            print("------------------------")

            is_correct = input("✅ Is this response correct for your idea? (y/n): ")

            if is_correct.lower() == "y":
                db.add_task(
                    title=topic,
                    content=refined_content,
                    source="manual",
                    status="pending",
                    # Respects the niche slot logic from the scheduler
                    extra_data={
                        "niche": "general",
                        "niche_slot": slot_name,
                        "source_url": "Manual Input",
                    },
                )
                success = True
                print("💾 Manual task saved to database!")
                break
            else:
                if attempt < 11:
                    feedback = input("💬 What should the AI change or improve?: ")

        if not success:
            print(
                "\n❌ Max attempts (5) reached. Please change the topic and run the script again."
            )
            return  # Halts the pipeline so it doesn't process an empty task

    else:
        print("---------------------------------------")
        print("🤖 Running Automated AI Scraper Flow...")
        scraper = NewsScraper()
        scraper.scrape_targeted_niche(forced_slot=slot_name)

    # 2. BRAIN (Scripting with Groq)
    print("---------------------------------------")
    brain = ScriptGenerator()
    brain.generate_script()

    # 3. VOICE (Async)
    print("---------------------------------------")
    voice = VoiceEngine()
    asyncio.run(voice.generate_audio())

    # 4. VISUALS
    print("---------------------------------------")
    visuals = VisualScout()
    visuals.download_visuals()

    # 5. ASSEMBLER
    print("---------------------------------------")
    assembler = VideoAssembler()
    assembler.assemble()

    # 6. UPLOAD PREP & UPLOAD
    print("---------------------------------------")
    prep = UploadManager()
    prep.prepare_package()

    # 7. UPLOAD TO YOUTUBE
    print("---------------------------------------")
    uploader = YouTubeUploader()
    uploader.upload_video()

    # 8. JSON LOGGING
    print("---------------------------------------")
    print("📝 Logging details to JSON...")

    db = DBManager()
    latest_task = db.collection.find_one(
        {"status": "uploaded"}, sort=[("uploaded_at", -1)]
    )

    if latest_task:
        log_entry = {
            "video_name": latest_task.get("title"),
            "youtube_id": latest_task.get("youtube_id"),
            "time_slot": slot_name,
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        log_file = "production_log.json"
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except:
                logs = []
        else:
            logs = []

        logs.append(log_entry)
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=4)

        print(f"✅ Log saved to: {log_file}")
    else:
        print("⚠️ Log skipped (No upload confirmed).")

    print("---------------------------------------")
    print("🧹 Cleaning up temporary metadata files...")

    temp_files = glob.glob("metadata_*.txt")
    for f in temp_files:
        try:
            os.remove(f)
            print(f"   🗑️ Deleted: {f}")
        except:
            pass

    print(f"\n✅ PIPELINE COMPLETE for {slot_name}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # 🟢 NEW: Set default to None. If None, it will calculate the current time slot.
    parser.add_argument(
        "slot",
        nargs="?",
        help="The time slot (morning/noon/evening/night)",
        default=None,
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Trigger the manual AI input refinement loop",
    )
    args = parser.parse_args()

    # Determine dynamic slot if none was provided in command line
    target_slot = args.slot
    if not target_slot:
        h = datetime.datetime.now().hour
        if 5 <= h < 12:
            target_slot = "morning"
        elif 12 <= h < 17:
            target_slot = "noon"
        elif 17 <= h < 21:
            target_slot = "evening"
        else:
            target_slot = "night"

    run_creation_pipeline(target_slot, args.manual)
