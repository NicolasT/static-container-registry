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

ARG ORAS_VERSION=0.12.0
RUN curl -#LO https://github.com/oras-project/oras/releases/download/v${ORAS_VERSION}/oras_${ORAS_VERSION}_linux_amd64.tar.gz \
      && \
      tar -zxf oras_${ORAS_VERSION}_*.tar.gz -C /usr/local/bin/ oras \
      && \
      rm oras_${ORAS_VERSION}_*.tar.gz

RUN [ "bash", "-c", "cd /usr/local/bin && bash <(curl -s https://raw.githubusercontent.com/pgrange/bash_unit/master/install.sh)" ]

COPY test.sh /
