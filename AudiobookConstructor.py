#!/usr/bin/env python3
import os
import random
import re
import subprocess
import sys
import time
import zipfile


# Sort chapters into nermerical order
def sort_chapters_numerically(s):
    return [
        int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)
    ]


def replace_special_characters(audio_dir, original_files):
    for i, filename in enumerate(original_files):
        if "'" in filename:
            os.rename(
                os.path.join(audio_dir, filename),
                os.path.join(audio_dir, filename.replace("'", "’")),
            )
            original_files[i] = filename.replace("'", "’")
        if "\\" in filename:
            os.rename(
                os.path.join(audio_dir, filename),
                os.path.join(audio_dir, filename.replace("\\", "-")),
            )
            original_files[i] = filename.replace("\\", "-")
        if "%" in filename:
            os.rename(
                os.path.join(audio_dir, filename),
                os.path.join(audio_dir, filename.replace("%", "pc")),
            )
            original_files[i] = filename.replace("%", "pc")

    return original_files


# Function to get audio codec of a file using ffprobe
def get_codec(audio_dir, file_path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            file_path,
        ],
        capture_output=True,
        text=True,
    )
    print(
        f"\n Converting {audio_dir.split('/')[-1]} ({result.stdout.strip()}) -> {audio_dir.split('/')[-1]}.m4b..."
    )
    return result.stdout.strip()


# Function to get duration of audio file in milliseconds using ffprobe
def get_duration(file_path):
    """Return duration of file in milliseconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            file_path,
        ],
        capture_output=True,
        text=True,
    )
    return int(float(result.stdout.strip()) * 1000)


# Write concat list file with absolute paths
def write_concat_list(audio_dir, temp_files):
    concat_list_path = os.path.join(audio_dir, "temp_concat_list.txt")
    with open(concat_list_path, "w") as concatlist:
        for temp_file in temp_files:
            if not os.path.exists(temp_file):
                print("Error: temp file not found:", temp_file)
                sys.exit(1)

            # Wrap path in single quotes, escaping existing single quotes
            # Additional special characters haven't yet been tested inc. ", &
            concatlist.write(
                f"file '{os.path.abspath(temp_file).replace("'", "''")}'\n"
            )

    return concat_list_path


# Write filelist.txt and chapters.txt
def generate_lists(audio_dir, original_files):
    filelist = os.path.join(audio_dir, "filelist.txt")
    chapters = os.path.join(audio_dir, "chapters.txt")

    # Write relative paths of audio files to filelist.txt; write_concat_list will handle quotes
    with open(filelist, "w") as filelisttxt:
        for fn in original_files:
            filelisttxt.write(f"{os.path.join(audio_dir, fn)}\n")

    total_duration = sum(
        get_duration(os.path.join(audio_dir, fn)) for fn in original_files
    )
    concat_list_path = os.path.join(audio_dir, "temp_concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        f.write("")

    # Generate chapters.txt metadata file with start/end times for each original file
    start = 0
    with open(chapters, "w") as chapterstxt:
        chapterstxt.write(";FFMETADATA1\n")
        for _, fn in enumerate(original_files, 1):
            end = start + get_duration(os.path.join(audio_dir, fn))
            # Use original filename for chapter title (preserve apostrophes)
            chapterstxt.write(
                f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={start}\nEND={end}\ntitle={fn.replace(' - ', ': ')}\n\n"
            )
            start = end

    return filelist, chapters, total_duration, concat_list_path


# Concatenate with re-encode (safer than copy)
def re_encode(concat_list_path, output_file):
    concat_command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",  # only show real errors here
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_list_path,
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        output_file,
    ]
    subprocess.run(concat_command, check=True)


# Add chapters metadata into a new file (ffmpeg cannot edit in-place)
def add_metadata(audio_dir, chapters, output_file, concat_list_path, author=None):
    final_file = os.path.join(audio_dir, f"{os.path.basename(audio_dir)}.m4b")
    temp_final_file = os.path.join(
        audio_dir, f"{os.path.basename(audio_dir)}_with_chapters.m4b"
    )

    # Detect and include cover image (if found)
    cover_file = None
    meta_insert = "and organising chapters"
    for ext in (".jpg", ".jpeg", ".png"):
        for f in os.listdir(audio_dir):
            if f.startswith(os.path.basename(audio_dir)) and f.lower().endswith(ext):
                cover_file = os.path.join(audio_dir, f)
                break
        if cover_file:
            break

    # Build FFmpeg command inputs
    chapter_command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        final_file,
        "-i",
        chapters,
    ]

    # Include the cover as an input
    if cover_file:
        chapter_command.extend(["-i", cover_file])
        meta_insert = ", organising chapters and adding cover"

    # Add metadata
    chapter_command.extend(
        [
            "-map_metadata",
            "1",
            "-c:a",
            "copy",
            "-metadata",
            f"title={os.path.basename(audio_dir)}",
            "-metadata",
            f"album={os.path.basename(audio_dir)}",
            "-metadata",
            f"author={author}",
            "-metadata",
            f"artist={author}",
        ]
    )

    # Attach cover to the output
    if cover_file:
        chapter_command.extend(
            [
                "-map",
                "0:a",  # map the audio
                "-map",
                "2",  # map the cover image
                "-c:v",
                "mjpeg",  # encode cover as MJPEG
                "-disposition:v",
                "attached_pic",
            ]
        )

    print(f"\n Re-encoding{meta_insert}...")
    re_encode(concat_list_path, output_file)

    chapter_command.append(temp_final_file)
    result = subprocess.run(chapter_command, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(temp_final_file):
        print("FFmpeg failed to add chapters and/or cover:\n", result.stderr)
        sys.exit(1)
    os.replace(temp_final_file, output_file)


# Cleanup temporary files
def clean_up(filelist, temp_files, concat_list_path, codec):
    # Archive all original files
    audio_dir = os.path.dirname(filelist)
    archive_file = os.path.join(
        audio_dir, f"{os.path.basename(audio_dir)}_originals.zip"
    )
    with zipfile.ZipFile(archive_file, "w", zipfile.ZIP_DEFLATED) as archive:
        with open(filelist, "r", encoding="utf-8") as f:
            for line in f:
                if os.path.exists(line.strip()) and (
                    line.strip().lower().endswith(f".{codec}")
                    or line.strip().lower().endswith(".jpg")
                    or line.strip().lower().endswith(".jpeg")
                    or line.strip().lower().endswith(".png")
                ):
                    archive.write(line.strip(), arcname=os.path.basename(line.strip()))
                    os.remove(line.strip())  # delete original after adding to archive

    # Delete temp and txt files
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    if os.path.exists(concat_list_path):
        os.remove(concat_list_path)
    os.remove(os.path.join(audio_dir, "filelist.txt"))
    os.remove(os.path.join(audio_dir, "chapters.txt"))


# Convert mp3 files to m4a, then concatenate with chapters metadata into m4b
def convert_mp3(
    author,
    filelist,
    chapters,
    audio_dir,
    total_duration,
    files,
    temp_files,
    cumulative_duration,
    start_time,
    output_file,
    concat_list_path,
    codec,
    verbose,
):
    # Convert each mp3 file to m4a with AAC codec and 128k bitrate
    with open(filelist, "r") as f:
        for line in f:
            path = line.strip()
            # Remove surrounding quotes if present
            if path.startswith("'") and path.endswith("'"):
                path = path[1:-1]
            elif path.startswith('"') and path.endswith('"'):
                path = path[1:-1]
            files.append(path)

    num = random.randint(8, 12)
    for _, input_file in enumerate(files, 1):
        duration = get_duration(input_file)
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        temp_file = os.path.join(audio_dir, f"{base_name}.m4a")

        # Remove temp file if exists
        if os.path.exists(temp_file):
            os.remove(temp_file)
        temp_files.append(temp_file)

        # Append to concat list
        with open(
            os.path.join(audio_dir, "temp_concat_list.txt"), "a", encoding="utf-8"
        ) as templist:
            # Wrap path in single quotes, escape any existing single quotes for FFmpeg concat
            safe_path = os.path.abspath(temp_file).replace("'", "'\\''")
            templist.write(f"file '{safe_path}'\n")

        command = [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            input_file,
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "44100",
            "-ac",
            "2",
            temp_file,
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"\nFFmpeg failed for {input_file}:\n{result.stderr}")
            sys.exit(1)

        if not os.path.exists(temp_file):
            print("Error: Failed to create temp file:", temp_file)
            sys.exit(1)

        # Show progress
        cumulative_duration += duration
        percentage = cumulative_duration / total_duration * 100
        elapsed_time = time.time() - start_time
        if cumulative_duration > 0:
            estimated_total_time = elapsed_time / (cumulative_duration / total_duration)
            eta_seconds = int(estimated_total_time - elapsed_time)
            eta_minutes = eta_seconds // 60
            eta_seconds = eta_seconds % 60
            eta_str = f"{eta_minutes}m {eta_seconds}s"

        # Print progress after every chapter
        if verbose and int(percentage) != 100:
            print(f"   Progress: {percentage:.1f}%\t{base_name}\n    ETA: ~{eta_str}")
        # Print progress every N%
        elif int(percentage) % num == 0 and int(percentage) != 100:
            print(f"   Progress: {percentage:.1f}%\t{base_name}\n    ETA: ~{eta_str}")

    add_metadata(audio_dir, chapters, output_file, concat_list_path, author)
    clean_up(filelist, temp_files, concat_list_path, codec)


def main():
    # Clear the terminal screen before starting
    subprocess.Popen(["clear"])
    time.sleep(0.1)

    # Verify command syntax
    if len(sys.argv) < 3:
        print(
            "Usage: python AudiobookConstructor.py <audiobook_directory> <author> [--verbose]"
        )
        sys.exit(1)

    audio_dir = sys.argv[1]
    author = sys.argv[2]
    # Check if the provided directory exists
    if not os.path.isdir(audio_dir):
        print(f"Error: Directory '{audio_dir}' does not exist.")
        sys.exit(1)

    verbose = False
    if "--verbose" in sys.argv:
        verbose = True

    files = []
    temp_files = []
    cumulative_duration = 0
    start_time = time.time()
    output_file = os.path.join(audio_dir, f"{os.path.basename(audio_dir)}.m4b")

    # List all audio files with supported extensions in directory
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

    # Replace single quotes in filenames with backticks to prevent FFmpeg concat issues
    original_files = replace_special_characters(audio_dir, original_files)

    filelist, chapters, total_duration, concat_list_path = generate_lists(
        audio_dir, original_files
    )

    # Detect codec for conversion decision
    codec = get_codec(audio_dir, os.path.join(audio_dir, original_files[-1]))
    if codec == "mp3":
        convert_mp3(
            author,
            filelist,
            chapters,
            audio_dir,
            total_duration,
            files,
            temp_files,
            cumulative_duration,
            start_time,
            output_file,
            concat_list_path,
            codec,
            verbose,
        )
    elif codec == "aac":
        pass
    else:
        print(f"File codec for {audio_dir} is {codec} and not supported.")
        sys.exit(1)

    print(f"\n Completed conversion for {audio_dir.split('/')[-1]}\n\n\n")


if __name__ == "__main__":
    main()
