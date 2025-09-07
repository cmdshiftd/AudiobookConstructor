import os
import subprocess


# Directory containing your audio book directories
AUDIO_DIRS = [
    "Quicksilver",
    "TheInnovators",
    "StartWithWhy",
    "Kissinger",
    "BenjaminFranklin",
]  # change to your folders


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


def convert_mp3(filelist, chapters, audio_dir):
    subprocess.run(
        [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            filelist,
            "-i",
            chapters,
            "-map_metadata",
            "1",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            f"{audio_dir}/{audio_dir.split('/')[-1]}.m4b",
        ],
        capture_output=True,
        text=True,
    )


def main():
    for audio_dir in AUDIO_DIRS:
        audio_dir = f"./{audio_dir}"
        filelist = os.path.join(audio_dir, "filelist.txt")
        chapters = os.path.join(audio_dir, "chapters.txt")
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

        # Create filelist.txt
        with open(filelist, "w") as f:
            for fn in files:
                f.write(f"file '{os.path.abspath(os.path.join(audio_dir, fn))}'\n")

        # Create chapters.txt
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

        # Identify codec to convert correctly
        codec = get_codec(os.path.join(audio_dir, fn))
        print(
            f"Converting {audio_dir.split("/")[-1]} ({codec}) to {audio_dir.split("/")[-1]}/{audio_dir.split('/')[-1]}.m4b..."
        )
        if codec == "mp3":
            convert_mp3(filelist, chapters, audio_dir)
            print(
                f"\n\n\n\n\n\nCompleted conversion for: {audio_dir.split('/')[-1]}\n\n"
            )
        elif codec == "aac":
            pass
        else:
            print(f"File codec for {audio_dir} is {codec} and not supported.")


if __name__ == "__main__":
    main()
