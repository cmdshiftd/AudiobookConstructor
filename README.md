# AudiobookConstructor
Maker audiobooks from existing individual audio files.

## Installation
Download [FFmpeg](https://ffmpeg.org) and install/build for your platform.


## Usage

`python3 AudiobookConstructor.py`

<br>

__Ensure you have your audio files in a directory, and that directory is alongside AudiobookConstructor.py and the file names are the correct respective Chapter names__

_.../AudiobookConstructor/_<br>
&emsp;&emsp;&emsp;&emsp;- _Harry Potter and the Philosopher's Stone/_<br>
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;- _Chapter 1 - The Boy Who Lived.mp3_<br>
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;- _Chapter 2 - The Vanishing Glass.mp3_<br>
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;- _Chapter 3 - The Letter from No One.mp3_<br>
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;- _Chapter 3 - The Keeper of the Keys.mp3_<br>
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;- _..._<br>
&emsp;&emsp;&emsp;&emsp;- _AudiobookConstructor.py_<br>
<br><br>

If the books has an Introduction, Forward or Afterword, name them as follows:
* Chapter 0-0 - Introduction
* Chapter 0-1 - Forward
* Chapter (Last+1) - Afterward