#!/usr/bin/env python3
# $ pip install openai-whisper

import whisper
import sys


def find_phrase_in_audio(audio_file, phrase="chapter 7"):
    # Load Whisper model (choose "base" for faster, "small/medium/large" for more accuracy)
    model = whisper.load_model("base")

    print(f"Transcribing {audio_file} ... this may take a while")
    result = model.transcribe(audio_file)

    matches = []
    for seg in result["segments"]:
        text = seg["text"].lower()
        if phrase.lower() in text:
            matches.append(
                {"start": seg["start"], "end": seg["end"], "text": seg["text"]}
            )
    return matches


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_chapter.py <audiofile.mp3>")
        sys.exit(1)

    audio_file = sys.argv[1]
    hits = find_phrase_in_audio(audio_file, phrase="Chapter 7")

    if hits:
        print("\nFound 'Chapter 7' at:")
        for h in hits:
            start_min = int(h["start"] // 60)
            start_sec = int(h["start"] % 60)
            print(f" - {start_min:02d}:{start_sec:02d} → {h['text']}")
    else:
        print("No occurrences of 'Chapter 7' found.")
