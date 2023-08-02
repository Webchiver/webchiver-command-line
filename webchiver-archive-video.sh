#!/bin/bash
cd "${0%/*}"
pwd
pipenv run python3 webchiver-archive-video.py $*
