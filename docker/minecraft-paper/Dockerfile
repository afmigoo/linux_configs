FROM eclipse-temurin:25-jre AS rcon-builder
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git \
      build-essential
RUN git clone https://github.com/Tiiffi/mcrcon.git /opt/mcrcon \
 && cd /opt/mcrcon \
 && make

FROM alpine:latest AS jar-downloader
RUN wget -O /opt/paper.jar https://fill-data.papermc.io/v1/objects/542288423062864e56969a44c6927b860152cb827c65ff5f841178602bc99e9a/paper-26.1.2-71.jar

FROM eclipse-temurin:25-jre
WORKDIR /data
COPY --from=jar-downloader /opt/paper.jar /opt/paper.jar
COPY --from=rcon-builder /opt/mcrcon/mcrcon /usr/local/bin/mcrcon
ENTRYPOINT ["sh", "-c", "java ${JAVA_OPTS:--Xms2G -Xmx2G} -jar /opt/paper.jar --nogui"]
