FROM eclipse-temurin:17-jre-jammy@sha256:1e38389ecd9e5c444e40d4385be4a4a5f56a836a38a6e41c099810c32ec1c595

ENV GRAPHOPPER_VERSION=11.0

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /opt/graphhopper /data \
    && curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
        --output /opt/graphhopper/graphhopper-web.jar \
        https://repo1.maven.org/maven2/com/graphhopper/graphhopper-web/11.0/graphhopper-web-11.0.jar \
    && echo 'b59c024afe172ec6ec85b6327006c3138ec58c7d0bcd26253d0e42853f613def  /opt/graphhopper/graphhopper-web.jar' \
        | sha256sum --check --strict \
    && groupadd --gid 10001 graphhopper \
    && useradd --uid 10001 --gid graphhopper --no-create-home --shell /usr/sbin/nologin graphhopper \
    && chown graphhopper:graphhopper /data

COPY --chmod=0444 config.yml /opt/graphhopper/config.yml
COPY --chmod=0555 entrypoint.sh /opt/graphhopper/entrypoint.sh

USER 10001:10001
WORKDIR /opt/graphhopper
EXPOSE 8989
ENTRYPOINT ["/opt/graphhopper/entrypoint.sh"]
