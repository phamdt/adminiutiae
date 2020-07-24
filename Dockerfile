########## base target ##########
FROM golang:1.14 AS base

ADD . /app
WORKDIR /app

CMD go run main.go

########## dev target ##########
FROM base AS dev

RUN go get github.com/pilu/fresh

CMD fresh