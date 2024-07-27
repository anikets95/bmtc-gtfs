# syntax=docker/dockerfile:1
FROM node:slim

RUN apt update && apt upgrade -y

RUN apt install -y chromium

RUN npm install -g gtfs-to-html

CMD [ "bash" ]