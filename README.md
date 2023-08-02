
This program allows you to archive videos to your Webchiver ([webchiver.com](https://www.webchiver.com))account from Youtube, Vimeo, and many other sites. This tool is a simple wrapper around <a href="https://github.com/yt-dlp/yt-dlp">yt-dlp</a> and is not in any way affiliated with Youtube. It is your responsibility to follow the terms of service of whichever site from which you are downloading videos.

1. [Download the current version](https://github.com/Webchiver/webchiver-command-line/archive/refs/heads/main.zip) and unzip into a local directory. Or clone the repository with `git`.
2. Open the installion folder in a terminal or command line.
3. Verify that [`python3` is installed](https://wiki.python.org/moin/BeginnersGuide/Download).
4. Install [pipenv](https://pipenv.pypa.io/en/latest/)
5. Install dependencies: `pipenv install`
6. Run the script to archive a video. You will be prompted for configuration the first time you run the script.
```
pipenv run python3 webchiver-archive-video.py <url-of-video>
# Eg.
pipenv run python3 webchiver-archive-video.py  https://www.youtube.com/watch?v=dQw4w9WgXcQ
```
7. Optional: Add a command alias for your script
```
echo "alias webchiver-archive-video='$PWD/webchiver-archive-video.sh'" >> ~/.bashrc
source ~/.bashrc
```
Now you will be able to archive a video from the command line by typing `webchiver-archive-video <url-of-video>` without having to go to the directory where you checked out the script.




