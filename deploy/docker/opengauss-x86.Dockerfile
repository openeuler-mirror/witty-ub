ARG BASE_IMAGE=hub-harbor.oepkgs.net/neocopilot/opengauss@sha256:4fd44608ca3571d3ceb5bc2bc5cbcde131dde2ed2b8068ff3f58effc8c60d885
FROM ${BASE_IMAGE} AS opengauss-base

FROM ${BASE_IMAGE}

USER root
RUN rm -rf /usr/local/opengauss && \
    mkdir -p /usr/local/opengauss && \
    chown omm:omm /usr/local/opengauss
COPY --chown=omm:omm rootfs/ /usr/local/opengauss/

# chparser is shipped as an add-on in the RAG base image, not in the
# openGauss-Server package produced by build.sh.  Replacing GAUSSHOME without
# restoring it leaves the persisted `chinese` text-search catalog entries
# pointing at a missing $libdir/chparser and breaks both document writes and
# hybrid searches.  Keep a package-provided copy when one exists; otherwise
# restore the add-on from the exact base image used for this build.
COPY --from=opengauss-base /usr/local/opengauss/lib/postgresql/chparser.so /tmp/witty-chparser/lib/postgresql/chparser.so
COPY --from=opengauss-base /usr/local/opengauss/share/postgresql/extension/chparser.control /tmp/witty-chparser/share/postgresql/extension/chparser.control
COPY --from=opengauss-base /usr/local/opengauss/share/postgresql/extension/chparser--1.0.sql /tmp/witty-chparser/share/postgresql/extension/chparser--1.0.sql
COPY --from=opengauss-base /usr/local/opengauss/share/postgresql/tsearch_data/dict.utf8.xdb /tmp/witty-chparser/share/postgresql/tsearch_data/dict.utf8.xdb
RUN if [ ! -f /usr/local/opengauss/lib/postgresql/chparser.so ]; then \
        install -o omm -g omm -m 0755 \
            /tmp/witty-chparser/lib/postgresql/chparser.so \
            /usr/local/opengauss/lib/postgresql/chparser.so; \
    fi && \
    if [ ! -f /usr/local/opengauss/share/postgresql/extension/chparser.control ]; then \
        install -o omm -g omm -m 0644 \
            /tmp/witty-chparser/share/postgresql/extension/chparser.control \
            /usr/local/opengauss/share/postgresql/extension/chparser.control; \
    fi && \
    if [ ! -f /usr/local/opengauss/share/postgresql/extension/chparser--1.0.sql ]; then \
        install -o omm -g omm -m 0644 \
            /tmp/witty-chparser/share/postgresql/extension/chparser--1.0.sql \
            /usr/local/opengauss/share/postgresql/extension/chparser--1.0.sql; \
    fi && \
    if [ ! -f /usr/local/opengauss/share/postgresql/tsearch_data/dict.utf8.xdb ]; then \
        install -o omm -g omm -m 0644 \
            /tmp/witty-chparser/share/postgresql/tsearch_data/dict.utf8.xdb \
            /usr/local/opengauss/share/postgresql/tsearch_data/dict.utf8.xdb; \
    fi && \
    rm -rf /tmp/witty-chparser

LABEL org.opencontainers.image.title="openGauss for Witty RAG" \
      org.opencontainers.image.description="AVX2 openGauss datavec build"
