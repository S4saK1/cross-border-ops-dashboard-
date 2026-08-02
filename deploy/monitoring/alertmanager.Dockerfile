# P0-3: 自定义 alertmanager 镜像，包含 envsubst 以支持模板变量替换
# 官方 prom/alertmanager 镜像是无包管理器的精简镜像，无法直接 apk add；
# 改为 alpine 基座 + 多阶段复制官方二进制。
FROM prom/alertmanager:v0.27.0 AS upstream
FROM alpine:3.20
COPY --from=upstream /bin/alertmanager /bin/alertmanager
COPY --from=upstream /bin/amtool /bin/amtool
COPY --from=upstream /etc/alertmanager /etc/alertmanager
RUN apk add --no-cache gettext && \
    mkdir -p /alertmanager && \
    chown -R nobody:nobody /alertmanager /etc/alertmanager
USER nobody
