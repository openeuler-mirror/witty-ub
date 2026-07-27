# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.

ARG BASE_IMAGE=witty-ub-base:latest

# ============================================
# Stage 1: Build C++ binaries (based on base image)
# ============================================
FROM ${BASE_IMAGE} AS builder-cpp

WORKDIR /build
COPY . .

RUN mkdir -p build && cd build && \
    cmake .. && \
    make -j$(nproc)

# ============================================
# Stage 2: Runtime image (based on base image)
# ============================================
FROM ${BASE_IMAGE}

LABEL maintainer="witty-ub"
LABEL description="Witty-UB: Fault localization tool for superpods with Lingqu(UB) architecture"

# Copy C++ binaries from builder
COPY --from=builder-cpp /build/build/src/witty-ub-log /usr/bin/
COPY --from=builder-cpp /build/build/src/witty-ub-topo /usr/bin/
COPY --from=builder-cpp /build/build/src/witty-ub-diag-tool /usr/bin/

# Copy data files
COPY data/view-vis /var/witty-ub/data/view-vis/
COPY data/failure_mode_tree.json /var/witty-ub/data/
COPY data/kvcache/kvcache_conn_fault_mode.json /var/witty-ub/data/kvcache/
COPY data/urma/urma_failure_mode.json /var/witty-ub/data/urma/
COPY config/diagnosis_config.toml /var/witty-ub/config/
COPY config/opencode.json /var/witty-ub/config/
COPY config/agents/witty-ub-diagnostician.md /var/witty-ub/config/agents/

# Copy web frontend (pre-built locally)
COPY src/web/dist /var/witty-ub/web/

# Copy nginx configuration (container-optimized)
COPY docker/nginx.conf /etc/witty-ub/web/nginx.conf

# Copy latency plugin
COPY src/plugins/latency/ENUM /var/witty-ub/latency/ENUM/
COPY src/plugins/latency/access /var/witty-ub/latency/access/
COPY src/plugins/latency/common /var/witty-ub/latency/common/
COPY src/plugins/latency/config /var/witty-ub/latency/config/
COPY src/plugins/latency/database /var/witty-ub/latency/database/
COPY src/plugins/latency/detect /var/witty-ub/latency/detect/
COPY src/plugins/latency/exceptions /var/witty-ub/latency/exceptions/
COPY src/plugins/latency/parse /var/witty-ub/latency/parse/
COPY src/plugins/latency/regex /var/witty-ub/latency/regex/
COPY src/plugins/latency/routers /var/witty-ub/latency/routers/
COPY src/plugins/latency/schemas /var/witty-ub/latency/schemas/
COPY src/plugins/latency/services /var/witty-ub/latency/services/
COPY src/plugins/latency/task /var/witty-ub/latency/task/
COPY src/plugins/latency/__init__.py /var/witty-ub/latency/

# Set permissions
RUN chmod 0755 /usr/bin/witty-ub-log /usr/bin/witty-ub-topo /usr/bin/witty-ub-diag-tool && \
    find /var/witty-ub/data -type f -exec chmod 0640 {} \; && \
    find /var/witty-ub/config -type f -exec chmod 0640 {} \; && \
    find /var/witty-ub/web -type d -exec chmod 0755 {} \; && \
    find /var/witty-ub/web -type f -exec chmod 0644 {} \;

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose ports
# 8080: Web UI (nginx)
# 9772: Latency plugin API (FastAPI)
# 4096: OpenCode server
EXPOSE 8080 9772 4096

# Volumes for persistent data
VOLUME ["/var/witty-ub/data", "/var/log/witty-ub"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9772/health_check || exit 1

ENTRYPOINT ["/entrypoint.sh"]
