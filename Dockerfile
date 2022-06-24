########## build target ##########
FROM golang:1.18-alpine AS build

WORKDIR /app

RUN apk add curl
RUN curl -L -o scc.zip https://github.com/boyter/scc/releases/download/v2.12.0/scc-2.12.0-i386-unknown-linux.zip
RUN unzip scc.zip
RUN rm scc.zip

ADD ./go.mod /app/go.mod
ADD ./go.sum /app/go.sum

RUN go mod download
ADD ./src /app/src
ADD ./pkg /app/pkg
ADD ./cmd/api /app/cmd/api

RUN go build /app/cmd/api/main.go


###################### DEV STAGE ######################
#
# This stage is what is used in development. The primary difference is that
# we install a hotreloading tool to update the API as changes
# are made to the various go files.
FROM build AS dev
WORKDIR /app

# download hot reload tool
RUN curl -sSfL https://raw.githubusercontent.com/cosmtrek/air/master/install.sh | sh -s -- -b $(go env GOPATH)/bin
ADD .air.toml .

CMD ["air", "-c", ".air.toml"]



########## runtime target ##########
FROM alpine:3.12 as runtime

WORKDIR /app

COPY --from=build /app/adminiutiae .
COPY --from=build /app/scc .

# put scc into the path so that the app can find it
ENV PATH="/app:${PATH}"


EXPOSE 8080
CMD [ "./adminiutiae" ]
