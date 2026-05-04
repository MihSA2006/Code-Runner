FROM alpine:3.19
RUN apk add --no-cache gcc musl-dev
RUN adduser -D -s /bin/sh runner
WORKDIR /code
USER runner
