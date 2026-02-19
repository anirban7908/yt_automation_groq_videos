import os
import whisper
import moviepy.video.fx as vfx
from moviepy import (
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,  # 🟢 NEW: Added VideoFileClip
    concatenate_videoclips,
)
from core.db_manager import DBManager

FONT_PATH = r"C:\Windows\Fonts\arial.ttf"

class VideoAssembler:
    def __init__(self):
        self.db = DBManager()
        self.model = whisper.load_model("base")

    def assemble(self):
        task = self.db.collection.find_one({"status": "ready_to_assemble"})
        if not task:
            return

        scenes = task.get("script_data", [])
        folder = task["folder_path"]
        video_title = task.get("title", "").upper()
        print(f"🎞️ Assembling {len(scenes)} segments with dynamic Video/Image handling...")

        final_clips = []

        for i, scene in enumerate(scenes):
            audio_path = scene["audio_path"]
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            visual_paths = scene["image_paths"] # Holds both .mp4 and .jpg paths now
            img_duration = duration / len(visual_paths)

            scene_clips = []
            for path in visual_paths:
                try:
                    # 🟢 NEW: Dynamic File Handling (Video vs Image)
                    if path.endswith(".mp4"):
                        clip = VideoFileClip(path).without_audio()
                        
                        # Fix duration: If video is too short, loop it. If too long, trim it.
                        if clip.duration < img_duration:
                            clip = clip.with_effects([vfx.Loop(duration=img_duration)])
                        else:
                            clip = clip.subclipped(0, img_duration)
                    else:
                        # Fallback for static images (e.g. Hero Google image or placebolder)
                        clip = (
                            ImageClip(path)
                            .with_duration(img_duration)
                            .with_effects([vfx.Resize(lambda t: 1 + 0.04 * t)]) # Keep zoom for static images only
                        )

                    # 🟢 Standardize Resolution/Crop for YouTube Shorts (1080x1920)
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
                scene_video = concatenate_videoclips(scene_clips).with_audio(audio_clip)

                # Title Hook logic (Same as before)
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

        # Combine Scenes & Generate Captions
        full_video = concatenate_videoclips(final_clips)
        full_audio_path = os.path.join(folder, "FULL_AUDIO_TEMP.mp3")
        full_video.audio.write_audiofile(full_audio_path)

        print("📝 Generating Captions...")
        result = self.model.transcribe(full_audio_path, word_timestamps=True)
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
            preset="medium",
            logger="bar",
        )

        self.db.collection.update_one(
            {"_id": task["_id"]},
            {"$set": {"status": "ready_to_upload", "final_video_path": out_path}},
        )
        print(f"🎉 Synchronized Video Ready: {out_path}")