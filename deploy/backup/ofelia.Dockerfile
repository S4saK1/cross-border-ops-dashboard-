# P0-4: Custom ofelia image with pg_dump and gzip for backup jobs
FROM mcuadros/ofelia:latest
USER root
RUN apk add --no-cache postgresql-client gzip gnupg rclone
