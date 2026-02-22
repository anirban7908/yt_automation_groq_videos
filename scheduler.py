import schedule
import time
import subprocess
import datetime
import sys

# Define the python executable (uses the current venv)
PYTHON_EXEC = sys.executable


def job(slot):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n🔔 [{timestamp}] TRIGGERING AUTOMATION: {slot.upper()}")

    try:
        # 🟢 FIX: Execute main.py directly from the root directory
        subprocess.run([PYTHON_EXEC, "main.py", slot], check=True)

        print(f"✅ [{slot.upper()}] JOB FINISHED.")

    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR in {slot} job: {e}")


# --- 📅 THE SCHEDULE ---
# Adjust times as needed
schedule.every().day.at("17:30").do(job, slot="morning")  # Motivation
schedule.every().day.at("19:30").do(job, slot="noon")  # Space
schedule.every().day.at("21:30").do(job, slot="evening")  # Nature
schedule.every().day.at("23:30").do(job, slot="night")  # History

print("===================================================")
print("🤖 THE KNOWLEDGE SPECTRUM: GROQ AUTOPILOT ENGAGED")
print("   - Schedule: 4 Times Daily")
print("   - Press Ctrl+C to stop")
print("===================================================")

# Loop forever
while True:
    schedule.run_pending()
    time.sleep(60)
