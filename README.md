# AudiobookConstructor
Make audiobooks from existing individual audio files, as easy as Ab-C!


## Installation
Install/build [FFmpeg](https://ffmpeg.org) for your platform.


## Usage

`python3 AudiobookConstructor.py <audiobook_directory/title> <author> [--verbose]`

<br>

### Example

`python3 AudiobookConstructor.py "Harry Potter and the Philosopher's Stone" "J. K. Rowling"`

<br>

__Ensure the audio files are named as the respective chapters and are within a directory named the book title. The book title directory must exist alongside AudiobookConstructor.py:__

_.../AudiobookConstructor/_<br>
&emsp;&emsp;- _AudiobookConstructor.py_<br>
&emsp;&emsp;- _Harry Potter and the Philosopher's Stone/_<br>
&emsp;&emsp;&emsp;&emsp;- _Harry Potter and the Philosopher's Stone.jpg_<br>
&emsp;&emsp;&emsp;&emsp;- _Chapter 1 - The Boy Who Lived.mp3_<br>
&emsp;&emsp;&emsp;&emsp;- _Chapter 2 - The Vanishing Glass.mp3_<br>
&emsp;&emsp;&emsp;&emsp;- _..._<br>
<br>

If the books has an Introduction, Forward or Afterword, name them as follows:
* Chapter 0.0 - Introduction
* Chapter 0.1 - Forward
* Chapter (Last+1) - Afterward