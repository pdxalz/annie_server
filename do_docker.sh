#!/bin/bash
docker run --rm --name anniedock --env-file .env -v $PWD/winddata:/winddata -p 80:8000/tcp -v roosterpict:/rooster annie_img
