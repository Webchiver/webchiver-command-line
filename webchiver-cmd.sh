#!/bin/bash
cd "${0%/*}"
pipenv run python3 webchiver-archive-video.py $*
