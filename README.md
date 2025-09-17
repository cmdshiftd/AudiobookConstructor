# AudiobookConstructor
Make audiobooks from a single MP3, as easy as Ab-C!


## Installation
Install/build [FFmpeg](https://ffmpeg.org) for your platform.<br>
`python3 -m venv <virtual_env> && source <virtual_env>/bin/activate`<br>
`pip install -r requirements.txt`<br>

## Usage

`python3 AudiobookConstructor.py <audiobook_directory/title>.mp3 <author>`

<br>

### Example

`python3 AudiobookConstructor.py "Harry Potter and the Philosopher's Stone.mp3" "J. K. Rowling"`

<br>

_Ensure the single audio file is in the **same** directory **AudiobookConstructor.py** and <audio_file_name>**.jpg**:_

_.../AudiobookConstructor/_<br>
&emsp;&emsp;- _AudiobookConstructor.py_<br>
&emsp;&emsp;- _Harry Potter and the Philosopher's Stone.mp3_<br>
&emsp;&emsp;- _Harry Potter and the Philosopher's Stone.jpg_<br>
&emsp;&emsp;- _..._<br>

You will have to extract segments such as Introduction, Epilogue, Foreword or Afterword etc. manually. And it is advised to name them as follows:
* Chapter 0.0 - Introduction
* Chapter 0.1 - Foreword
* Chapter (Last+1) - Afterword
<br><br>
