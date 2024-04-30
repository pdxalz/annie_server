#!/bin/bash
docker run --rm -v $PWD/winddata:/winddata -p 80:8000/tcp -e SERVER_URL=http://192.168.68.113 -v roosterpict:/rooster  annie_img
