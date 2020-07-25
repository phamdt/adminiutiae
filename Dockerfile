########## build target ##########
FROM golang:1.14-alpine AS build


ADD ./go.mod /app/go.mod
ADD ./go.sum /app/go.sum

WORKDIR /app

RUN go mod download
ADD ./src /app/src
ADD ./main.go /app/main.go

RUN go build


########## dev target ##########
FROM build AS dev

RUN go get github.com/pilu/fresh

CMD fresh


########## runtime target ##########
FROM alpine:3.12 as runtime

COPY --from=build /app/adminiutiae .
RUN apk add curl
RUN curl -o scc.zip https://github.com/boyter/scc/releases/download/v2.12.0/scc-2.12.0-i386-unknown-linux.zip

EXPOSE 8080
ENTRYPOINT [ "./adminiutiae" ]
