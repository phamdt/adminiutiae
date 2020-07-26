########## build target ##########
FROM golang:1.14-alpine AS build


ADD ./go.mod /app/go.mod
ADD ./go.sum /app/go.sum

WORKDIR /app

RUN go mod download

RUN apk add curl
RUN curl -L -o scc.zip https://github.com/boyter/scc/releases/download/v2.12.0/scc-2.12.0-i386-unknown-linux.zip
RUN unzip scc.zip
RUN rm scc.zip

ADD ./src /app/src
ADD ./cmd/githubscc/main.go /app/main.go

RUN GOOS=linux GOARCH=amd64 go build -o githubscc


########## runtime target ##########
FROM alpine:3.12 as runtime

WORKDIR /app

COPY --from=build /app/githubscc .
COPY --from=build /app/scc .

# put scc into the path so that the app can find it
ENV PATH="/app:${PATH}"


EXPOSE 8080
CMD [ "./githubscc" ]
