# P0-3: 自定义 alertmanager 镜像，包含 envsubst 以支持模板变量替换
FROM prom/alertmanager:v0.27.0
USER root
RUN apk add --no-cache gettext
USER nobody
