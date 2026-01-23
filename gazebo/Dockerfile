FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg lsb-release \
  && rm -rf /var/lib/apt/lists/*

# Repositório OSRF (Gazebo)
RUN curl -sSL https://packages.osrfoundation.org/gazebo.gpg \
  | gpg --dearmor -o /usr/share/keyrings/gazebo-archive-keyring.gpg && \
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gazebo-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
  > /etc/apt/sources.list.d/gazebo-stable.list

# Gazebo Sim (Jetty)
RUN apt-get update && apt-get install -y --no-install-recommends \
  gz-jetty \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /ws
CMD ["bash"]

