#!/usr/bin/env python3
"""EPUB to audiobook conversion module."""

import os
import sys
from tqdm import tqdm

# Optional imports for epub/pdf conversion
try:
    from ebooklib import epub
    from bs4 import BeautifulSoup
    from gtts import gTTS
    from pydub import AudioSegment
    EPUB_SUPPORT = True
except ImportError:
    EPUB_SUPPORT = False


def epub_to_text(epub_path):
    """Extract text content from an EPUB file."""
    book = epub.read_epub(epub_path)
    text_parts = []
    for item in book.get_items():
        if item.get_type() == epub.EpubHtml:
            soup = BeautifulSoup(item.get_body_content(), "html.parser")
            text_parts.append(soup.get_text())
    return "\n".join(text_parts)


def text_to_speech(text, output_path, lang="en"):
    """Convert text to speech and save as MP3."""
    max_chunk = 4000  # safe limit for Google TTS
    chunks = [text[i : i + max_chunk] for i in range(0, len(text), max_chunk)]

    print(f"\n Converting text to speech in {len(chunks)} chunks...")
    audio_segments = []

    for idx, chunk in enumerate(tqdm(chunks, desc="Generating audio", unit="chunk")):
        tts = gTTS(chunk, lang=lang)
        tmp_file = f"part_{idx}.mp3"
        tts.save(tmp_file)
        audio_segments.append(AudioSegment.from_mp3(tmp_file))
        os.remove(tmp_file)

    print("\n Concatenating audio segments...")
    final_audio = sum(audio_segments)
    final_audio.export(output_path, format="mp3")


def epub_to_audiobook(epub_file, output_file):
    """Convert EPUB file to MP3 audiobook."""
    if not EPUB_SUPPORT:
        print("\n ❌ Error: EPUB support not available. Install required packages:\n")
        print("    pip install ebooklib beautifulsoup4 gtts pydub\n\n")
        sys.exit(1)

    print(f"\n Extracting text from '{epub_file}'...")
    text = epub_to_text(epub_file)
    text_to_speech(text, output_file)
    print(f"\n ✅ Audiobook saved as '{output_file}'")
