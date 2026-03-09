FROM emscripten/emsdk:4.0.23 AS base-image

RUN \
  apt-get update -y && \
  apt-get install -y \
  bash \
  build-essential \
  cmake \
  curl \
  git \
  libffi-dev \
  libgdbm-dev \
  libncurses5-dev \
  libnss3-dev \
  libreadline-dev \
  libsqlite3-dev \
  libssl-dev \
  libbz2-dev \
  npm \
  python3 \
  python3-setuptools \
  zlib1g-dev
  
COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/

WORKDIR /rapidjson/
RUN \
  git clone --depth 1 -b v1.1.0 https://github.com/Tencent/rapidjson.git . 

ENV OCCT_VERSION=V7_9_3
WORKDIR /occt/
RUN \
  curl -L "https://github.com/Open-Cascade-SAS/OCCT/archive/refs/tags/${OCCT_VERSION}.tar.gz" -o occt.tar.gz && \
  tar -xzf occt.tar.gz && \
  mv OCCT-*/* . && \
  mv OCCT-*/.* . || true && \
  rmdir OCCT-* || true && \
  rm occt.tar.gz

  
FROM base-image AS stage-uv

COPY src/pyproject.toml /opencascade.js/src/pyproject.toml
COPY src/uv.lock /opencascade.js/src/uv.lock
WORKDIR /opencascade.js/src/
RUN uv sync
  
  # =============================================================
  
  # FROM base-image AS stage-patched
# RUN python3 /opencascade.js/src/apply_patches.py

# =============================================================

FROM stage-uv AS stage-compiled

COPY src/compile_sources.py /opencascade.js/src/compile_sources.py
COPY src/filters /opencascade.js/src/filters/

WORKDIR /opencascade.js/src/

ARG threading=single-threaded
ARG release=false
ENV threading=$threading

RUN uv run compile_sources.py ${threading} ${release}

# =============================================================

FROM stage-compiled AS stage-bindings

COPY src/filters/ /opencascade.js/src/filters
COPY src/wasmGenerator/ /opencascade.js/src/wasmGenerator 
COPY src/tu_info.py /opencascade.js/src/tu_info.py
COPY src/bindings.py /opencascade.js/src/bindings.py
COPY src/generate_bindings.py /opencascade.js/src/generate_bindings.py
COPY src/common.py /opencascade.js/src/common.py

WORKDIR /opencascade.js/src/

RUN uv run generate_bindings.py

# =============================================================

FROM stage-bindings AS custom-build-image
COPY src/compile_bindings.py /opencascade.js/src/compile_bindings.py

WORKDIR /opencascade.js/src/
RUN \
  uv run compile_bindings.py ${threading} ${release} && \
  chmod -R 777 /opencascade.js/ && \
  chmod -R 777 /occt

ENTRYPOINT ["/opencascade.js/src/build_yaml.py"]
