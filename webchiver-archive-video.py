#!/usr/bin/env python3

import argparse
from datetime import datetime
from hashlib import md5
import json
import os
import re
import shutil
import sys
from urllib.parse import urlencode

from plumbum import local, FG
from plumbum.cmd import mvn, cat, chmod
import requests


"""
selenium_available = False
try:
    from selenium import webdriver
    selenium_available = bool(shutil.which('chromedriver'))
except:
    print('No selenium available')
"""

"""
import logging
import contextlib
from http.client import HTTPConnection # py3
HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
"""

title_re = re.compile('<title>([^<]*)</title>')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="The URL to archive")
    parser.add_argument("--webchiver-server-url", help="The URL of the webchiver server")
    parser.add_argument("--webchiver-api-key", help="The URL of the webchiver server")
    args = parser.parse_args()


    
    url = args.url
    if not '://' in url:
        raise Exception('First argument must be the URL you want to archive')
    api_key = args.webchiver_api_key
    server_url = args.webchiver_server_url
    if not api_key or not server_url:
        with open(os.environ['HOME'] + '/.webchiver.config', 'r') as f:
            conf = json.load(f)
            api_key = api_key or conf['apiKeyForSubmit']
            server_url = server_url or conf['serverUrl']
    urlhash = md5(url.encode()).hexdigest()
    folder = 'webchiver-tmp-' + urlhash
    if not os.path.isdir(folder):
        os.makedirs(folder)
    if os.path.isfile(folder + '/webchiver-upload-succeeded'):
        print('Video has already been uploaded')
        return
    os.chdir(folder)
    print('Download with yt-dlp into folder ' + folder)
    result = local['yt-dlp'][url] & FG

    r = requests.get(url)
    html = r.content.decode('utf8')
    m = title_re.search(html)
    title = m.group(1)

    data = {
        'title': title,
        'url': url,
        'saveNewVersion': True
    }

    """
    if selenium_available:
        print('get screenshot')
        DRIVER = 'chromedriver'
        driver = webdriver.Chrome(DRIVER)
        driver.get(url)
        screenshot = driver.save_screenshot('my_screenshot.png')
        driver.quit()
        print('got screenshot')
    """
        #import pdb; pdb.set_trace()

    video_paths = []
    for path in os.listdir('.'):
        if not os.path.isfile(path):
            continue
        name, ext = os.path.splitext(path)
        ext = ext[1:]
        if ext not in VIDEO_EXTENSIONS:
            print("Skipping non video or audio file ", path)
            continue
        video_paths.append((path, ext))
    if not video_paths:
        print("No videos found")
        exit()
    files = {}
    if shutil.which('ffmpeg') and not os.path.isfile('first-video-image.jpg'):
        first_video_path = video_paths[0][0]
        print('Make thumbnail using ffmpeg')
        local['ffmpeg']['-ss']['00:00:01.00']['-i'][first_video_path]['-vf']['scale=320:320:force_original_aspect_ratio=decrease']['-vframes']['1']['first-video-image.jpg'] & FG
    if os.path.isfile('first-video-image.jpg'):
        f = open('first-video-image.jpg', 'rb')
        files['screenshot'] = f
        #print(files)
        #ffmpeg -ss 00:00:01.00 -i input.mp4 -vf 'scale=320:320:force_original_aspect_ratio=decrease' -vframes 1 output.jpg
    
        
    print('Submit article metadata ' + url + '  ' + title)
    response = requests.post(
        server_url + '/api/articles/submit',
        headers={
            'x-requested-by': 'console',
            'Authorization': 'Bearer ' + api_key
        },
        data=data,
        files=files
    )
    if response.status_code != 200:
        print(response)
        print(response.content)
        raise Exception("Error saving metadata")

    
    for path, ext in video_paths:
        query_params = dict(
            url=url,
            videoExtension=ext,
            videoKey=md5(path.encode()).hexdigest()
        )
        
        with open(path, 'rb') as f:
            upload_url = server_url + '/api/articles/video-stream-upload'
            print('Upload video ' + path + ' Upload URL ' + upload_url)
            response = requests.post(
                upload_url,
                params=query_params,
                headers={
                    'x-requested-by': 'console',
                    'Authorization': 'Bearer ' + api_key
                },
                data=f
            )
            
            if response.status_code != 200:
                print(response)
                print(response.content)
                raise Exception("Error saving video")
            else:
                print("Succeeded uploading video")
    print("Video uploads completed")
        
VIDEO_EXTENSIONS = [
	"3g2",
	"3gp",
	"aaf",
	"asf",
	"avchd",
	"avi",
	"drc",
	"flv",
	"m2v",
	"m3u8",
	"m4p",
	"m4v",
	"mkv",
	"mng",
	"mov",
	"mp2",
	"mp4",
	"mpe",
	"mpeg",
	"mpg",
	"mpv",
	"mxf",
	"nsv",
	"ogg",
	"ogv",
	"qt",
	"rm",
	"rmvb",
	"roq",
	"svi",
	"vob",
	"webm",
	"wmv",
	"yuv",
  "wav",
    "bwf",
    "raw",
    "aiff",
    "flac",
    "m4a",
    "pac",
    "tta",
    "wv",
    "ast",
    "aac",
    "mp2",
    "mp3",
    "mp4",
    "amr",
    "s3m",
    "3gp",
    "act",
    "au",
    "dct",
    "dss",
    "gsm",
    "m4p",
    "mmf",
    "mpc",
    "ogg",
    "oga",
    "opus",
    "ra",
    "sln",
    "vox"    
]
            
main()    

