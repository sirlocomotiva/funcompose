# 7 Days to Die dedicated server for funcompose.
#
# The game only ships x86_64 Linux server files, so build and run this image as
# linux/amd64. The game is installed with DepotDownloader, not steamcmd:
# steamcmd is a 32-bit program and crashes under emulation on Apple Silicon.
FROM ubuntu:24.04

ARG DEPOT_DOWNLOADER_VERSION=3.4.0

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl python3 unzip \
    && curl -fsSL -o /tmp/depotdownloader.zip \
        "https://github.com/SteamRE/DepotDownloader/releases/download/DepotDownloader_${DEPOT_DOWNLOADER_VERSION}/DepotDownloader-linux-x64.zip" \
    && unzip -q /tmp/depotdownloader.zip -d /opt/depotdownloader \
    && chmod 755 /opt/depotdownloader/DepotDownloader \
    && rm /tmp/depotdownloader.zip \
    && apt-get purge -y curl unzip \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

ENV DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/sdtd

COPY sdtd.py /usr/local/bin/sdtd
RUN chmod 755 /usr/local/bin/sdtd && mkdir -p /server /data /config /home/sdtd

# 26900 TCP+UDP is the game port. The game also uses the next UDP ports.
EXPOSE 26900/tcp 26900/udp 26901/udp 26902/udp 26903/udp

ENTRYPOINT ["sdtd"]
CMD ["run"]
