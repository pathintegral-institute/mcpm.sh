# build frpc
FROM golang:1.19 AS building
WORKDIR /
RUN git clone https://github.com/huggingface/frp.git
WORKDIR /frp
RUN make frpc

# run frpc
FROM alpine:3

COPY --from=building /frp/bin/frpc /usr/bin/frpc

COPY frpc.ini /etc/frp/frpc.ini

ENTRYPOINT ["/usr/bin/frpc", "-c", "/etc/frp/frpc.ini"]
