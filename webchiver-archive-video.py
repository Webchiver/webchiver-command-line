#!/usr/bin/env python3

import argparse
from datetime import datetime
from hashlib import md5
import base64
import json
import os
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import urlencode

from plumbum import local, FG
from plumbum.cmd import mvn, cat, chmod
import requests
import toml


title_re = re.compile('<title>([^<]*)</title>')
meta_description_re = re.compile(r'<meta\s+name=[\'"]description[\'"]\s+content="([^"]*)"\s*>')
meta_description_sq_re = re.compile(r"<meta\s+name=['\"]description['\"]\s+content='([^']*)'\s*>")

class Settings:
    def __init__(self, server_url, api_key):
        self.server_url = server_url
        self.api_key = api_key

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="The URL to archive")
    parser.add_argument("--server-url", help="The URL of the webchiver server", required=False)
    parser.add_argument("--api-key", help="The URL of the webchiver server", required=False)
    args = parser.parse_args()

    
    settings = load_settings(args)
    
    url = args.url
    if not '://' in url:
        raise Exception('First argument must be the URL you want to archive')
    api_key = settings.api_key
    server_url = settings.server_url
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
    title = ''
    m = title_re.search(html)
    if m and m.group(1):
        title = m.group(1)

    description = ''
    m = meta_description_re.search(html)
    if not m:
        m = meta_description_sq_re.search(html)
    if m and m.group(1):
        description = m.group(1)

    # TODO: get description, get plaintext

    metadata = dict(
        title=title,
        url=url,
        source=html,
        binaryFile=False,
        description=description,
        isPlainTextFile=False,
        skipTagChanges=True
    )

   
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
    screenshot_data_url = ''
    if shutil.which('ffmpeg') and not os.path.isfile('first-video-image.jpg'):
        first_video_path = video_paths[0][0]
        print('Make thumbnail using ffmpeg')
        local['ffmpeg']['-ss']['00:00:01.00']['-i'][first_video_path]['-vf']['scale=320:320:force_original_aspect_ratio=decrease']['-vframes']['1']['first-video-image.jpg'] & FG
    if os.path.isfile('first-video-image.jpg'):
        with open('first-video-image.jpg', 'rb') as f:
            image_bytes = f.read()
            data_b64 = base64.b64encode(image_bytes).decode('ascii')
            screenshot_data_url = 'data:image/jpeg;base64,' + data_b64
        #ffmpeg -ss 00:00:01.00 -i input.mp4 -vf 'scale=320:320:force_original_aspect_ratio=decrease' -vframes 1 output.jpg
    
        
    print('Submit article metadata ' + url + '  ' + title)
    response = requests.post(
        server_url + '/api/articles/get-or-insert-page-metadata',
        headers={
            'x-requested-by': 'console',
            'Authorization': 'Bearer ' + api_key
        },
        data=json.dumps(metadata)
    )
    if response.status_code != 200:
        print(response)
        print(response.content)
        raise Exception("Error saving metadata")
    if screenshot_data_url:
        response = requests.post(
            server_url + '/api/articles/save-screenshot',
            headers={
                'x-requested-by': 'console',
                'Authorization': 'Bearer ' + api_key
            },
            data=json.dumps(dict(
                url=url,
                screenshotDataUrl=screenshot_data_url
            ))
        )
        print('Response from screenshot save ', response)

    # TODO: upload first video image as screenshot
    
    for path, ext in video_paths:
        query_params = dict(
            url=url,
            canonicalUrl=url + '#' + path,
            videoExtension=ext
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
    

def load_settings(args):
    conf_file_path = get_conf_file_path()

    api_key = args.api_key
    server_url = args.server_url
    server_conf = None
    settings = None
    if (not api_key or not server_url) and conf_file_path.is_file():
        settings = toml.load(conf_file_path)
        print(settings)
        for server in settings.get('servers', []):
            if not server_url:
                server_conf = server
                break
            elif server_url == server['url']:
                server_conf = server
        if server_conf:
            print('CONF ', server_conf)
            api_key = server_conf.get('api_key')
            server_url = server_conf.get('url')

    if not server_url:
        api_key = None
        server_url = input("What server do you want to connect to (Default https://app.webchiver.com)? ")
        if not server_url:
            server_url = "https://app.webchiver.com"
    url = server_url + '/api/account/command-line-ask-for-key'
    print("URL ", url)
    if not api_key:
        r = requests.post(
            url,
            headers={
                'x-requested-by': 'console'
            }
        )
        text = r.text
        print(r)
        d = json.loads(text)
        connection_secret = d['connectionSecret']
        input('Go to the following URL to approve the request, then return here and type enter: \n\n\t' + server_url + "/app/approve-connection?returnToKey=console&connectionSecret=" + connection_secret + "\n\n")
        r = requests.post(
            server_url + '/api/account/command-line-verify',
            data=json.dumps(dict(originConnectionSecret=connection_secret)),
            headers={
                'x-requested-by': 'console'
            }            
        )
        d = r.json()

        if not settings:
            settings = dict(servers=[])
        if not server_conf:
            server_conf = dict(
                url=server_url,
            )
        server_conf['api_key'] = d['apiPassword']
        server_conf['account_id'] = d['accountId']
        server_conf['account_guid'] = d['accountGuid']
        server_conf['user_id'] = d['userId']
        found = False
        for server in settings['servers']:
            if server_conf['url'] == server['url']:
                server.update(server_conf)
                found = True
        if not found:
            settings['servers'].append(server_conf)
        api_key = server_conf['api_key']
        server_url = server_conf['url']
        yn = input('Connection succeeded. Save api key to local file ' + str(conf_file_path) + '? Y/n')
        if yn == 'Y':
            with open(conf_file_path, 'w') as f:
                toml.dump(settings, f)
    return Settings(server_url, api_key)
    

    

def get_conf_file_path():
    config_home = os.environ.get('XDG_CONFIG_HOME')
    if not config_home:
        config_home = os.environ.get('LOCALAPPDATA')
    if not config_home and os.environ.get('HOME'):
        config_home = os.environ.get('HOME') + '/Library/Preferences'
        if not os.path.isdir(config_home):
            config_home = None
        if not config_home:
            config_home = os.environ.get('HOME') + '/.config'
            if not os.path.isdir(config_home):
                config_home = None
    if not config_home:
        config_home = os.environ.get('HOME') or os.environ.get('HOMEPATH')
        return Path(config_home) / Path('.webchiver-command-line.toml.conf')
    return Path(config_home) / Path('webchiver-command-line.toml.conf')


        
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

