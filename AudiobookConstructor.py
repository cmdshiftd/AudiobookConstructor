#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import time
import warnings

# Import from pages modules
from pages.epub_converter import epub_to_audiobook
from pages.chapter_splitter import split_chapters
from pages.audio_processor import (
    sort_chapters_numerically,
    get_codec,
    generate_lists,
    convert_mp3,
)
from pages.file_utils import (
    error_checking,
    replace_special_characters,
    clean_up,
)


def main():
    subprocess.Popen(["clear"])
    time.sleep(0.1)

    parser = argparse.ArgumentParser(
        description="Convert audiobook files to m4b format with chapters"
    )
    parser.add_argument(
        "audiobook_file", help="Path to the audiobook file (mp3, epub, or pdf)"
    )
    parser.add_argument("author", help="Author name for metadata")
    parser.add_argument(
        "--no-titles",
        action="store_true",
        help="Don't use chapter titles from chapter_titles.txt, only use chapter numbers",
    )
    parser.add_argument(
        "--from-epub",
        action="store_true",
        help="Convert from EPUB/PDF to MP3 first before processing",
    )

    args = parser.parse_args()

    warnings.filterwarnings("ignore")
    input_file = args.audiobook_file
    author = args.author
    use_titles = not args.no_titles

    # Handle EPUB/PDF conversion if requested
    if args.from_epub:
        if not input_file.lower().endswith((".epub", ".pdf")):
            print("\n ❌ Error: --from-epub flag requires an .epub or .pdf file\n\n")
            sys.exit(1)

        # Generate output MP3 filename
        audio_file = os.path.splitext(input_file)[0] + ".mp3"

        # Convert EPUB to MP3
        if input_file.lower().endswith(".epub"):
            epub_to_audiobook(input_file, audio_file)
        else:
            print(
                "\n ❌ Error: PDF conversion not yet implemented. Only EPUB is supported.\n\n"
            )
            sys.exit(1)
    else:
        audio_file = input_file

    audio_dir = audio_file.split(".")[0]

    book_cover = error_checking(audio_dir, audio_file)

    # Skip chapter extraction if --no-titles flag is set
    if args.no_titles:
        print(" Skipping chapter extraction (--no-titles flag set)...")
        print(" Converting single file without chapter extraction...")
        # Create directory and copy the original file as-is
        os.makedirs(audio_dir, exist_ok=True)
        import shutil
        single_file = os.path.join(audio_dir, os.path.basename(audio_file))
        shutil.copy2(audio_file, single_file)
        chapters = []
        non_chapters = {}
    else:
        # Extract chapters from original single audio file
        chapters, non_chapters = split_chapters(
            audio_file, output_dir=audio_dir, use_titles=use_titles
        )

        # Handle case where no chapters were found
        if not chapters:
            print(" Converting single file without chapter extraction...")
            # Create directory and copy the original file as-is
            os.makedirs(audio_dir, exist_ok=True)
            import shutil
            single_file = os.path.join(audio_dir, os.path.basename(audio_file))
            shutil.copy2(audio_file, single_file)
        else:
            # Get highest chapter number
            import re
            max_chapter = 0
            for ch in chapters:
                match = re.match(r"Chapter (\d+)", ch["chapter"])
                if match:
                    max_chapter = max(max_chapter, int(match.group(1)))

            print(
                f"\n Chapters 1 through {max_chapter} have been extracted successfully."
            )

    # Only show non-chapters prompt if we actually extracted chapters
    if not args.no_titles and chapters and len(non_chapters) > 0:
        print(
            "\n   Manual extraction is required for non-chapters.\n    === Potential non-chapter occurrences ==="
        )
        for keyword, timestamps in non_chapters.items():
            formatted_times = []
            for t in timestamps:
                start_min = int(t // 60)
                start_sec = int(t % 60)
                formatted_times.append(f"{start_min:02d}:{start_sec:02d}")
            print(f"    - '{keyword}':\t{', '.join(formatted_times)}")
        time.sleep(20)
        print()

        input("    Press any key to continue...\n")

    time.sleep(2)
    subprocess.Popen(["clear"])
    time.sleep(0.1)

    # Begin conversion and amalgamation of extracted chapters into single m4b file
    files = []
    temp_files = []
    cumulative_duration = 0
    start_time = time.time()
    output_file = os.path.join(audio_dir, f"{os.path.basename(audio_dir)}.m4b")

    original_files = sorted(
        [
            f
            for f in os.listdir(audio_dir)
            if f.lower().endswith((".mp3", ".m4a", ".aac"))
        ],
        key=sort_chapters_numerically,
    )
    if not original_files:
        print("No audio files found.")
        sys.exit(1)

    original_files = replace_special_characters(audio_dir, original_files)

    filelist, chapters_file, total_duration, concat_list_path = generate_lists(
        audio_dir, original_files
    )

    codec = get_codec(audio_dir, os.path.join(audio_dir, original_files[-1]))
    if codec == "mp3":
        convert_mp3(
            author,
            filelist,
            chapters_file,
            audio_dir,
            audio_file,
            book_cover,
            total_duration,
            files,
            temp_files,
            cumulative_duration,
            start_time,
            output_file,
            concat_list_path,
            use_titles,
        )
        clean_up(audio_dir, audio_file, use_titles)
    else:
        print(f"File codec for {audio_dir} is not mp3 and is not supported.")
        sys.exit(1)

    print(f"\n Completed conversion for '{audio_dir.split('/')[-1]}'\n\n\n")


if __name__ == "__main__":
    main()
