import os
import subprocess
import sys
import time


# Function to get audio codec of a file using ffprobe
def get_codec(file_path):
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


# Convert mp3 files to m4a, then concatenate with chapters metadata into m4b
def convert_mp3(filelist, chapters, audio_dir, total_duration):
    files = []
    with open(filelist, "r") as f:
        for line in f:
            if line.startswith("file "):
                path = line.strip().split("file ")[1].strip("'")
                files.append(path)

    temp_files = []
    cumulative_duration = 0
    start_time = time.time()

    # Convert each mp3 file to m4a with AAC codec and 128k bitrate
    for _, input_file in enumerate(files, 1):
        duration = get_duration(input_file)
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        temp_file = os.path.join(audio_dir, f"{base_name}.m4a")

        # Removing temp file if it already exists
        if os.path.exists(temp_file):
            os.remove(temp_file)
        temp_files.append(temp_file)

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
        subprocess.run(
            command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # Show progress
        cumulative_duration += duration
        percentage = cumulative_duration / total_duration * 100
        elapsed_time = time.time() - start_time
        if cumulative_duration > 0:
            estimated_total_time = elapsed_time / (cumulative_duration / total_duration)
            eta_seconds = int(estimated_total_time - elapsed_time)
            eta_minutes = eta_seconds // 60
            eta_seconds = eta_seconds % 60
            if eta_minutes == 0:
                eta_str = f"{eta_minutes}m"
            if eta_seconds == 0:
                eta_str = f"{eta_minutes}m"
            eta_str = f"{eta_minutes}m {eta_seconds}s"
        else:
            eta_str = "calculating..."

        print(
            f"\n  - Progress: {percentage:.1f}%\t{base_name}\n    ~{eta_str} remaining"
        )

    # Write concat list file with absolute paths
    concat_list_path = os.path.join(audio_dir, "temp_concat_list.txt")
    with open(concat_list_path, "w") as f:
        for temp_file in temp_files:
            abs_path = os.path.abspath(temp_file)
            f.write(f"file '{abs_path}'\n")

    output_file = os.path.join(audio_dir, f"{os.path.basename(audio_dir)}.m4b")

    # Concatenate with re-encode (safer than copy)
    concat_command = [
        "ffmpeg",
        "-hide_banner",
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

    # Add chapters metadata in a second pass
    chapter_command = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        output_file,
        "-i",
        chapters,
        "-map_metadata",
        "1",
        "-c:a",
        "copy",
        output_file,
    ]
    subprocess.run(chapter_command, check=True)

    # Cleanup temporary files
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    if os.path.exists(concat_list_path):
        os.remove(concat_list_path)

    print(f"\n  - Progress 100.0%: {os.path.basename(audio_dir)}.m4b completed\n")


def main():
    # Clear the terminal screen before starting
    subprocess.Popen(["clear"])
    time.sleep(0.2)

    if len(sys.argv) < 2:
        print("Usage: python AudiobookMaker.py <audiobook_directory>")
        sys.exit(1)

    audio_dir = sys.argv[1]

    # Check if the provided directory exists
    if not os.path.isdir(audio_dir):
        print(f"Error: Directory '{audio_dir}' does not exist.")
        sys.exit(1)

    filelist = os.path.join(audio_dir, "filelist.txt")
    chapters = os.path.join(audio_dir, "chapters.txt")
    # List all audio files with supported extensions in directory
    files = sorted(
        [
            f
            for f in os.listdir(audio_dir)
            if f.lower().endswith((".mp3", ".m4a", ".aac"))
        ]
    )
    if not files:
        print("No audio files found.")
        return

    # Write absolute paths of audio files to filelist.txt for ffmpeg concat input
    with open(filelist, "w") as f:
        for fn in files:
            f.write(f"file '{os.path.abspath(os.path.join(audio_dir, fn))}'\n")

    # Generate chapters.txt metadata file with start/end times for each file
    start = 0
    with open(chapters, "w") as f:
        f.write(";FFMETADATA1\n")
        for i, fn in enumerate(files, 1):
            dur = get_duration(os.path.join(audio_dir, fn))
            end = start + dur
            f.write("[CHAPTER]\n")
            f.write("TIMEBASE=1/1000\n")
            f.write(f"START={start}\n")
            f.write(f"END={end}\n")
            f.write(f"title=Chapter {i}: {fn}\n\n")
            start = end

    # Detect codec of last file for conversion decision
    codec = get_codec(os.path.join(audio_dir, fn))
    print(
        f"Converting {audio_dir.split('/')[-1]} ({codec}) to {audio_dir.split('/')[-1]}/{audio_dir.split('/')[-1]}.m4b..."
    )
    total_duration = sum(get_duration(os.path.join(audio_dir, fn)) for fn in files)
    if codec == "mp3":
        convert_mp3(filelist, chapters, audio_dir, total_duration)
    elif codec == "aac":
        pass
    else:
        print(f"File codec for {audio_dir} is {codec} and not supported.")
        sys.exit(1)
    print(f"\n\n\n\n\n\nCompleted conversion for: {audio_dir.split('/')[-1]}\n\n")


if __name__ == "__main__":
    main()
