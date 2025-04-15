# build frpc
FROM golang:1.19 AS building
WORKDIR /
RUN git clone https://github.com/huggingface/frp.git
WORKDIR /frp
RUN make frpc

# run frpc
FROM alpine:3

COPY --from=building /frp/bin/frpc /usr/bin/frpc

ENTRYPOINT ["/usr/bin/frpc"]