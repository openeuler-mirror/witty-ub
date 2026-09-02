# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.

ARG BASE_IMAGE=witty-ub-base:latest
ARG BASE_IMAGE_BACKEND=witty-ub-base-backend:latest
ARG BASE_IMAGE_FRONTEND=witty-ub-base-frontend:latest

# ============================================
# Stage 1: Build C++ binaries (based on All-in-One base, which has the toolchain)
# ============================================
FROM ${BASE_IMAGE} AS builder-cpp

WORKDIR /build
COPY . .

RUN mkdir -p build && cd build && \
    cmake .. && \
    make -j$(nproc) \
        witty-ub-log \
        witty-ub-topo \
        witty-ub-diag-tool \
        witty-ub-brpc-diag

# Compile tokenizer for experience-skill
RUN cd witty_ub_diagnostician/skills/experience-skill/scripts/src/experience_skill_cli/tokenizer && \
    bash build.sh

# ============================================
# Target: backend role image (FastAPI + C++ diagnosis tools + data)
# ============================================
FROM ${BASE_IMAGE_BACKEND} AS backend

LABEL maintainer="witty-ub"
LABEL description="Witty-UB backend image (FastAPI + C++ diagnosis tools)"

COPY --from=builder-cpp /build/build/src/witty-ub-log /usr/bin/
COPY --from=builder-cpp /build/build/src/witty-ub-topo /usr/bin/
COPY --from=builder-cpp /build/build/src/witty-ub-diag-tool /usr/bin/
COPY --from=builder-cpp /build/build/src/witty-ub-brpc-diag /usr/bin/

# Immutable packaged data seed; entrypoint refreshes the witty-ub-data volume.
COPY data/view-vis /usr/share/witty-ub/data/view-vis/
COPY data/failure_mode_tree.json /usr/share/witty-ub/data/
COPY data/kvcache/kvcache_failure_mode.json /usr/share/witty-ub/data/kvcache/
COPY data/kvcache/kvcache_error_code_info.json /var/witty-ub/data/kvcache/
COPY data/ubsocket /usr/share/witty-ub/data/ubsocket/
COPY data/umq /usr/share/witty-ub/data/umq/
COPY data/urma /usr/share/witty-ub/data/urma/
RUN find /usr/share/witty-ub/data -type f -exec chmod 0640 {} \; && \
    cp -a /usr/share/witty-ub/data/. /var/witty-ub/data/

COPY config/diagnosis_config.toml /var/witty-ub/config/

# Copy latency plugin
COPY src/plugins/latency/ENUM /var/witty-ub/latency/ENUM/
COPY src/plugins/latency/access /var/witty-ub/latency/access/
COPY src/plugins/latency/common /var/witty-ub/latency/common/
COPY src/plugins/latency/config /var/witty-ub/latency/config/
COPY src/plugins/latency/database /var/witty-ub/latency/database/
COPY src/plugins/latency/bucket /var/witty-ub/latency/bucket/
COPY src/plugins/latency/exceptions /var/witty-ub/latency/exceptions/
COPY src/plugins/latency/parse /var/witty-ub/latency/parse/
COPY src/plugins/latency/regex /var/witty-ub/latency/regex/
COPY src/plugins/latency/routers /var/witty-ub/latency/routers/
COPY src/plugins/latency/schemas /var/witty-ub/latency/schemas/
COPY src/plugins/latency/services /var/witty-ub/latency/services/
COPY src/plugins/latency/task /var/witty-ub/latency/task/
COPY deploy/deploy_opencode.sh /var/witty-ub/deploy/deploy_opencode.sh
COPY src/plugins/latency/__init__.py /var/witty-ub/latency/

RUN chmod 0755 /usr/bin/witty-ub-log /usr/bin/witty-ub-topo \
        /usr/bin/witty-ub-diag-tool /usr/bin/witty-ub-brpc-diag && \
    chmod 0755 /var/witty-ub/deploy/deploy_opencode.sh && \
    find /var/witty-ub/data -type f -exec chmod 0640 {} \; && \
    find /var/witty-ub/config -type f -exec chmod 0640 {} \;

COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/healthcheck.sh /healthcheck.sh
RUN chmod +x /entrypoint.sh /healthcheck.sh

ENV WITTY_ROLE=backend

EXPOSE 9772

VOLUME ["/var/witty-ub/data", "/var/log/witty-ub"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/healthcheck.sh"]

ENTRYPOINT ["/entrypoint.sh"]

# ============================================
# Target: frontend role image (Nginx + OpenCode + web dist)
# ============================================
FROM ${BASE_IMAGE_FRONTEND} AS frontend

LABEL maintainer="witty-ub"
LABEL description="Witty-UB frontend image (Nginx + OpenCode)"

# Copy witty_ub_diagnostician contents into .opencode directory
COPY witty_ub_diagnostician/ /var/witty-ub/witty_ub_diagnostician/.opencode/

# Copy compiled libsimple.so from builder
COPY --from=builder-cpp /build/witty_ub_diagnostician/skills/experience-skill/scripts/src/experience_skill_cli/tokenizer/simple-src/output/bin/libsimple.so /var/witty-ub/witty_ub_diagnostician/.opencode/skills/experience-skill/scripts/src/experience_skill_cli/tokenizer/simple-src/output/bin/

# Create symlink for libsimple.so and set up experience-skill venv
RUN cd /var/witty-ub/witty_ub_diagnostician/.opencode/skills/experience-skill/scripts/src/experience_skill_cli/tokenizer && \
    ln -sf simple-src/output/bin/libsimple.so libsimple && \
    cd /var/witty-ub/witty_ub_diagnostician/.opencode/skills/experience-skill/scripts && \
    /root/.local/bin/uv sync

# Copy web frontend (pre-built locally)
COPY src/web/dist /var/witty-ub/web/

# Copy nginx configuration (container-optimized default + template for split
# deployment; entrypoint renders the template with WITTY_BACKEND_URL/WITTY_AGENT_URL)
COPY docker/nginx.conf /etc/witty-ub/web/nginx.conf
COPY packaging/nginx/witty-ub-web.conf.template /etc/witty-ub/web/nginx.conf.template

RUN find /var/witty-ub/web -type d -exec chmod 0755 {} \; && \
    find /var/witty-ub/web -type f -exec chmod 0644 {} \; && \
    find /var/witty-ub/witty_ub_diagnostician -type d -exec chmod 0755 {} \; && \
    find /var/witty-ub/witty_ub_diagnostician -type f -exec chmod 0644 {} \; && \
    find /var/witty-ub/witty_ub_diagnostician -type f -name "*.sh" -exec chmod 0755 {} \;

COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/healthcheck.sh /healthcheck.sh
RUN chmod +x /entrypoint.sh /healthcheck.sh

ENV WITTY_ROLE=frontend

EXPOSE 8080 4096

VOLUME ["/var/log/witty-ub"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/healthcheck.sh"]

ENTRYPOINT ["/entrypoint.sh"]

# ============================================
# Target: All-in-One (default) — single-machine image with full workload
# ============================================
FROM ${BASE_IMAGE} AS all

LABEL maintainer="witty-ub"
LABEL description="Witty-UB: Fault localization tool for superpods with Lingqu(UB) architecture"

# Copy C++ binaries from builder
COPY --from=builder-cpp /build/build/src/witty-ub-log /usr/bin/
COPY --from=builder-cpp /build/build/src/witty-ub-topo /usr/bin/
COPY --from=builder-cpp /build/build/src/witty-ub-diag-tool /usr/bin/
COPY --from=builder-cpp /build/build/src/witty-ub-brpc-diag /usr/bin/

# Keep an immutable copy of packaged data so the entrypoint can refresh an
# existing witty-ub-data volume when the image is upgraded.
COPY data/view-vis /usr/share/witty-ub/data/view-vis/
COPY data/failure_mode_tree.json /usr/share/witty-ub/data/
COPY data/kvcache/kvcache_failure_mode.json /usr/share/witty-ub/data/kvcache/
COPY data/kvcache/kvcache_error_code_info.json /var/witty-ub/data/kvcache/
COPY data/ubsocket /usr/share/witty-ub/data/ubsocket/
COPY data/umq /usr/share/witty-ub/data/umq/
COPY data/urma /usr/share/witty-ub/data/urma/
RUN find /usr/share/witty-ub/data -type f -exec chmod 0640 {} \; && \
    cp -a /usr/share/witty-ub/data/. /var/witty-ub/data/

# Copy configuration files
COPY config/diagnosis_config.toml /var/witty-ub/config/

# Copy witty_ub_diagnostician contents into .opencode directory
COPY witty_ub_diagnostician/ /var/witty-ub/witty_ub_diagnostician/.opencode/

# Copy compiled libsimple.so from builder
COPY --from=builder-cpp /build/witty_ub_diagnostician/skills/experience-skill/scripts/src/experience_skill_cli/tokenizer/simple-src/output/bin/libsimple.so /var/witty-ub/witty_ub_diagnostician/.opencode/skills/experience-skill/scripts/src/experience_skill_cli/tokenizer/simple-src/output/bin/

# Copy web frontend (pre-built locally)
COPY src/web/dist /var/witty-ub/web/

# Copy nginx configuration (container-optimized default + template for split
# deployment; entrypoint renders the template with WITTY_BACKEND_URL/WITTY_AGENT_URL)
COPY docker/nginx.conf /etc/witty-ub/web/nginx.conf
COPY packaging/nginx/witty-ub-web.conf.template /etc/witty-ub/web/nginx.conf.template

# Copy latency plugin
COPY src/plugins/latency/ENUM /var/witty-ub/latency/ENUM/
COPY src/plugins/latency/access /var/witty-ub/latency/access/
COPY src/plugins/latency/common /var/witty-ub/latency/common/
COPY src/plugins/latency/config /var/witty-ub/latency/config/
COPY src/plugins/latency/database /var/witty-ub/latency/database/
COPY src/plugins/latency/bucket /var/witty-ub/latency/bucket/
COPY src/plugins/latency/exceptions /var/witty-ub/latency/exceptions/
COPY src/plugins/latency/parse /var/witty-ub/latency/parse/
COPY src/plugins/latency/regex /var/witty-ub/latency/regex/
COPY src/plugins/latency/routers /var/witty-ub/latency/routers/
COPY src/plugins/latency/schemas /var/witty-ub/latency/schemas/
COPY src/plugins/latency/services /var/witty-ub/latency/services/
COPY src/plugins/latency/task /var/witty-ub/latency/task/
COPY deploy/deploy_opencode.sh /var/witty-ub/deploy/deploy_opencode.sh
COPY src/plugins/latency/__init__.py /var/witty-ub/latency/

# Create symlink for libsimple.so and set up experience-skill venv
RUN cd /var/witty-ub/witty_ub_diagnostician/.opencode/skills/experience-skill/scripts/src/experience_skill_cli/tokenizer && \
    ln -sf simple-src/output/bin/libsimple.so libsimple && \
    cd /var/witty-ub/witty_ub_diagnostician/.opencode/skills/experience-skill/scripts && \
    /root/.local/bin/uv sync

# Set permissions
RUN chmod 0755 /usr/bin/witty-ub-log /usr/bin/witty-ub-topo \
        /usr/bin/witty-ub-diag-tool /usr/bin/witty-ub-brpc-diag && \
    chmod 0755 /var/witty-ub/deploy/deploy_opencode.sh && \
    find /var/witty-ub/data -type f -exec chmod 0640 {} \; && \
    find /var/witty-ub/config -type f -exec chmod 0640 {} \; && \
    find /var/witty-ub/web -type d -exec chmod 0755 {} \; && \
    find /var/witty-ub/web -type f -exec chmod 0644 {} \; && \
    find /var/witty-ub/witty_ub_diagnostician -type d -exec chmod 0755 {} \; && \
    find /var/witty-ub/witty_ub_diagnostician -type f -exec chmod 0644 {} \; && \
    find /var/witty-ub/witty_ub_diagnostician -type f -name "*.sh" -exec chmod 0755 {} \;

# Copy entrypoint & healthcheck scripts
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/healthcheck.sh /healthcheck.sh
RUN chmod +x /entrypoint.sh /healthcheck.sh

# Expose ports
# 8080: Web UI (nginx)
# 9772: Latency plugin API (FastAPI)
# 4096: OpenCode server
EXPOSE 8080 9772 4096

# Volumes for persistent data
VOLUME ["/var/witty-ub/data", "/var/log/witty-ub"]

# Health check (role-aware: frontend probes the remote backend)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/healthcheck.sh"]

ENTRYPOINT ["/entrypoint.sh"]
