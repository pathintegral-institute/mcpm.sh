# build frps
FROM golang:1.19 AS building
WORKDIR /
RUN git clone https://github.com/huggingface/frp.git
WORKDIR /frp
RUN make frps

# run frps
FROM alpine:3
COPY --from=building /frp/bin/frps /usr/bin/frps
RUN apk add curl

HEALTHCHECK --interval=1m --timeout=30s --retries=3 CMD curl --fail http://localhost:7001/healthz || exit 1

COPY frps.ini /etc/frp/frps.ini

ENTRYPOINT ["/usr/bin/frps", "-c", "/etc/frp/frps.ini"]
