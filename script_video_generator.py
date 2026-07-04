"""
Turn a list of (image, narration text) segments into a narrated video.

Pipeline per segment:
    1. Generate an AI voice narration audio file for the text (edge-tts,
       free Microsoft neural voices, no API key needed).
    2. Measure that audio's duration.
    3. Hold the matching image on screen for exactly that duration.
Then all segments are concatenated into one video.

Install:
    pip install moviepy edge-tts

Requires ffmpeg installed on your system (moviepy calls it under the hood).
Requires internet access (edge-tts talks to Microsoft's speech endpoint).

Usage:
    from script_video_generator import ScriptVideoGenerator

    generator = ScriptVideoGenerator(voice="en-US-AriaNeural")

    segments = [
        {"image": "panels/panel_01.png", "text": "Yes, for some reason, an image of twin babies keeps popping up in my mind."},
        {"image": "panels/panel_02.png", "text": "It has nothing to do with me."},
        {"image": "panels/panel_03.png", "text": "He's crying this hard over some babies?"},
    ]

    generator.build_video(segments, output_path="chapter_1.mp4")
"""

import os
import asyncio
import edge_tts
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips


class ScriptVideoGenerator:
    """
    Builds a narrated slideshow-style video from (image, text) segments.

    Args:
        voice: an edge-tts voice name. Run `edge-tts --list-voices` in your
               terminal to see all options. A few good English ones:
                 "en-US-AriaNeural"   (US female)
                 "en-US-GuyNeural"    (US male)
                 "en-GB-SoniaNeural"  (UK female)
                 "en-GB-RyanNeural"   (UK male)
        rate: speech rate adjustment, e.g. "+10%" or "-15%". Default "+0%".
        fps: output video frame rate.
        target_width: if set, every image is resized to this width (keeping
                      aspect ratio) before being placed in the video. Useful
                      when your panels have different widths, since all
                      clips in a video need matching dimensions.
        temp_dir: folder used to store the generated per-segment audio files.
        keep_audio_files: if False, deletes the temp audio files after the
                           video is built.
    """

    def __init__(
        self,
        voice="en-US-AriaNeural",
        rate="+0%",
        fps=24,
        target_width=800,
        temp_dir="tts_audio_temp",
        keep_audio_files=False,
    ):
        self.voice = voice
        self.rate = rate
        self.fps = fps
        self.target_width = target_width
        self.temp_dir = temp_dir
        self.keep_audio_files = keep_audio_files
        os.makedirs(self.temp_dir, exist_ok=True)

    def _generate_narration(self, text, out_path):
        """Generate one TTS audio file for a chunk of text."""

        async def _run():
            communicate = edge_tts.Communicate(text, voice=self.voice, rate=self.rate)
            await communicate.save(out_path)

        asyncio.run(_run())

    def _build_clip(self, image_path, text, index):
        """Create one ImageClip+audio segment for a single (image, text) pair."""
        audio_path = os.path.join(self.temp_dir, f"segment_{index:03d}.mp3")
        self._generate_narration(text, audio_path)

        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration

        img_clip = ImageClip(image_path).with_duration(duration)

        if self.target_width:
            img_clip = img_clip.resized(width=self.target_width)

        img_clip = img_clip.with_audio(audio_clip)
        return img_clip, audio_path

    def build_video(self, segments, output_path="output.mp4", pad_seconds=0.3):
        """
        Build the full narrated video.

        Args:
            segments: list of dicts, each with:
                - "image": path to the image file for this segment
                - "text": the narration text to read aloud over that image
            output_path: where to write the final mp4.
            pad_seconds: small silence added after each segment's narration
                         so cuts don't feel rushed. Set to 0 to disable.

        Returns:
            output_path
        """
        clips = []
        audio_paths = []

        for i, seg in enumerate(segments):
            print(f"[{i+1}/{len(segments)}] Generating narration + clip for: {seg['image']}")
            clip, audio_path = self._build_clip(seg["image"], seg["text"], i)
            if pad_seconds:
                clip = clip.with_duration(clip.duration + pad_seconds)
            clips.append(clip)
            audio_paths.append(audio_path)

        print("Concatenating clips...")
        final = concatenate_videoclips(clips, method="compose")

        print(f"Writing video to {output_path} ...")
        final.write_videofile(output_path, fps=self.fps, codec="libx264", audio_codec="aac")

        if not self.keep_audio_files:
            for p in audio_paths:
                try:
                    os.remove(p)
                except OSError:
                    pass

        return output_path


if __name__ == "__main__":
    # Example: pair up panels from ComicPanelSplitter with matching script lines
    segments = [
        {"image": "panels/panel_01.png", "text": "Yes, for some reason, an image of twin babies keeps popping up in my mind. I feel like I won't be able to see them again for some reason. But... it does not matter."},
        {"image": "panels/panel_02.png", "text": "It has nothing to do with me."},
        {"image": "panels/panel_03.png", "text": "Nothing to do... with me..."},
    ]

    generator = ScriptVideoGenerator(voice="en-US-GuyNeural")
    generator.build_video(segments, output_path="chapter_output.mp4")
