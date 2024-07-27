FROM rust:slim

RUN apt update && apt upgrade -y
RUN apt install git pkg-config libssl-dev -y

RUN git clone https://github.com/etalab/transport-validator/

ADD run.sh .
RUN chmod 777 run.sh