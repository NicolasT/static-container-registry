ARG OS_VERSION=20.04
FROM docker.io/ubuntu:$OS_VERSION

ARG OS_VERSION
ARG REPOSITORY=https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable
RUN export DEBIAN_FRONTEND=noninteractive \
      && \
      apt-get update \
      && \
      apt-get install -y curl software-properties-common \
      && \
      echo "deb ${REPOSITORY}/xUbuntu_${OS_VERSION}/ /" > /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list \
      && \
      curl -L ${REPOSITORY}/xUbuntu_${OS_VERSION}/Release.key | apt-key add - \
      && \
      apt-get update \
      && \
      apt-get install -y skopeo

RUN apt-get install -y \
      hardlink

COPY provision-images.sh /provision-images.sh
