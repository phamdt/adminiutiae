########## build target ##########
FROM golang:1.14-alpine AS build


ADD ./go.mod /app/go.mod
ADD ./go.sum /app/go.sum

WORKDIR /app

RUN go mod download
ADD ./src /app/src
ADD ./main.go /app/main.go

RUN go build
RUN apk add curl
RUN curl -L -o scc.zip https://github.com/boyter/scc/releases/download/v2.12.0/scc-2.12.0-i386-unknown-linux.zip
RUN unzip scc.zip
RUN rm scc.zip

########## dev target ##########
FROM build AS dev

RUN go get github.com/pilu/fresh

CMD fresh


########## runtime target ##########
FROM alpine:3.12 as runtime

WORKDIR /app

COPY --from=build /app/adminiutiae .
COPY --from=build /app/scc .

# put scc into the path so that the app can find it
ENV PATH="/app:${PATH}"


EXPOSE 8080
ENTRYPOINT [ "./adminiutiae" ]
