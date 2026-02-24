import os
import whisper
import moviepy.video.fx as vfx
from moviepy import (
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)
from core.db_manager import DBManager

FONT_PATH = r"C:\Windows\Fonts\arial.ttf"

# Dynamically find the absolute path to your project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class VideoAssembler:
    def __init__(self):
        self.db = DBManager()
        self.model = whisper.load_model("base")

    def assemble(self):
        task = self.db.collection.find_one({"status": "ready_to_assemble"})
        if not task:
            return

        scenes = task.get("script_data", [])
        folder = os.path.normpath(os.path.join(PROJECT_ROOT, task["folder_path"]))
        video_title = task.get("title", "").upper()
        print(f"🎞️ Assembling {len(scenes)} segments with memory optimization...")

        final_clips = []

        for i, scene in enumerate(scenes):
            audio_path = os.path.normpath(
                os.path.join(PROJECT_ROOT, scene["audio_path"])
            )

            if not os.path.exists(audio_path):
                print(f"⚠️ Missing Audio File: {audio_path} - Skipping scene {i}")
                continue

            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            visual_paths = scene.get("image_paths", [])

            if not visual_paths:
                continue

            img_duration = duration / len(visual_paths)

            scene_clips = []
            for raw_path in visual_paths:
                try:
                    path = os.path.normpath(os.path.join(PROJECT_ROOT, raw_path))

                    if not os.path.exists(path):
                        print(f"⚠️ Missing Visual File: {path}")
                        continue

                    if path.endswith(".mp4"):
                        # 🟢 FIX: Removed the buggy target_resolution that was causing the landscape stretch/memory leak.
                        # We just load the video without audio to save memory.
                        clip = VideoFileClip(path, audio=False)

                        if clip.duration < img_duration:
                            clip = clip.with_effects([vfx.Loop(duration=img_duration)])
                        else:
                            clip = clip.subclipped(0, img_duration)
                    else:
                        clip = ImageClip(path).with_duration(img_duration)

                    # Standardize Resolution/Crop correctly for 9:16 Shorts
                    clip = clip.resized(height=1920)
                    if clip.w < 1080:
                        clip = clip.resized(width=1080)
                    clip = clip.cropped(
                        x_center=clip.w / 2,
                        y_center=clip.h / 2,
                        width=1080,
                        height=1920,
                    )
                    scene_clips.append(clip)
                except Exception as e:
                    print(f"⚠️ Error processing visual {path}: {e}")

            if scene_clips:
                # 🟢 FIX: Reverted to method="chain" to prevent visual glitches between different stock clips
                scene_video = concatenate_videoclips(
                    scene_clips, method="chain"
                ).with_audio(audio_clip)

                if i == 0:
                    try:
                        title_clip = (
                            TextClip(
                                text=video_title,
                                font=FONT_PATH,
                                font_size=80,
                                color="yellow",
                                stroke_color="black",
                                stroke_width=5,
                                method="caption",
                                size=(900, None),
                                margin=(20, 20),
                            )
                            .with_position("center")
                            .with_duration(min(duration, 3))
                            .with_start(0)
                        )
                        scene_video = CompositeVideoClip([scene_video, title_clip])
                    except Exception as e:
                        print(f"⚠️ Could not add title hook: {e}")

                final_clips.append(scene_video)

        if not final_clips:
            print("\n🚨 CRITICAL: No clips were successfully processed!")
            return

        # Combine Scenes & Generate Captions
        full_video = concatenate_videoclips(final_clips, method="chain")
        os.makedirs(folder, exist_ok=True)

        full_audio_path = os.path.join(folder, "FULL_AUDIO_TEMP.mp3")
        full_video.audio.write_audiofile(full_audio_path, logger=None)

        print("📝 Generating Captions...")
        result = self.model.transcribe(
            full_audio_path, word_timestamps=True, fp16=False
        )
        caption_clips = []

        for segment in result["segments"]:
            for word in segment["words"]:
                txt = (
                    TextClip(
                        text=word["word"].strip().upper(),
                        font=FONT_PATH,
                        font_size=75,
                        color="white",
                        stroke_color="black",
                        stroke_width=4,
                        method="caption",
                        size=(1000, None),
                        margin=(20, 20),
                    )
                    .with_start(word["start"])
                    .with_duration(word["end"] - word["start"])
                    .with_position(("center", 1600))
                )
                caption_clips.append(txt)

        final_export = CompositeVideoClip(
            [full_video] + caption_clips, size=(1080, 1920)
        )
        out_path = os.path.join(folder, "FINAL_VIDEO.mp4")

        final_export.write_videofile(
            out_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            bitrate="8000k",
            threads=4,
            preset="ultrafast",
            logger="bar",
        )

        self.db.collection.update_one(
            {"_id": task["_id"]},
            {"$set": {"status": "ready_to_upload", "final_video_path": out_path}},
        )
        print(f"🎉 Synchronized Video Ready: {out_path}")

        if os.path.exists(full_audio_path):
            os.remove(full_audio_path)
            print("🧹 Cleaned up temporary audio file.")
