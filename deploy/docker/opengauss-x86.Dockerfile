ARG BASE_IMAGE=hub-harbor.oepkgs.net/neocopilot/opengauss@sha256:4fd44608ca3571d3ceb5bc2bc5cbcde131dde2ed2b8068ff3f58effc8c60d885
FROM ${BASE_IMAGE}

USER root
RUN rm -rf /usr/local/opengauss && \
    mkdir -p /usr/local/opengauss && \
    chown omm:omm /usr/local/opengauss
COPY --chown=omm:omm rootfs/ /usr/local/opengauss/

LABEL org.opencontainers.image.title="openGauss for Witty RAG" \
      org.opencontainers.image.description="AVX2 openGauss datavec build"
