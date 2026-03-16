FROM emscripten/emsdk:4.0.23 AS base-image

ARG multithreaded=0
ENV BUILD_MULTITHREADED=${multithreaded}

RUN \
  apt-get update -y && \
  apt-get install -y \
  build-essential \
  curl \
  git \
  vim

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

COPY headers/Standard_Version.hxx /occt/src/Standard/Standard_Version.hxx
  
FROM base-image AS stage-uv

COPY src/pyproject.toml /opencascade.js/src/pyproject.toml
COPY src/uv.lock /opencascade.js/src/uv.lock
WORKDIR /opencascade.js/src/
RUN uv sync
  
# =============================================================
  
# FROM base-image AS stage-patched
# RUN python3 /opencascade.js/src/apply_patches.py

# =============================================================

FROM stage-uv AS stage-compile-sources

COPY src/common.py /opencascade.js/src/common.py
COPY src/compile_sources.py /opencascade.js/src/compile_sources.py
COPY src/filters /opencascade.js/src/filters/

WORKDIR /opencascade.js/src/

RUN uv run compile_sources.py

# =============================================================

FROM stage-uv AS stage-preambles

COPY src/filters /opencascade.js/src/filters/
COPY src/common.py /opencascade.js/src/common.py
COPY src/wasm_gen/ /opencascade.js/src/wasm_gen
COPY src/generate_preambles.py /opencascade.js/src/generate_preambles.py

WORKDIR /opencascade.js/src/

RUN uv run generate_preambles.py

# =============================================================

FROM stage-preambles AS stage-bindgen

COPY --from=stage-preambles /opencascade.js/build/preambles.json /opencascade.js/build/preambles.json
COPY src/tu_info.py /opencascade.js/src/tu_info.py
COPY src/bindings.py /opencascade.js/src/bindings.py
COPY src/generate_bindings.py /opencascade.js/src/generate_bindings.py

WORKDIR /opencascade.js/src/

RUN uv run generate_bindings.py

# =============================================================

FROM stage-bindgen AS stage-compile-bindings

COPY src/compile_bindings.py /opencascade.js/src/compile_bindings.py
COPY src/build_schema_def.py /opencascade.js/src/build_schema_def.py

WORKDIR /opencascade.js/src/

RUN uv run compile_bindings.py

# =============================================================

FROM stage-compile-bindings AS final-image

COPY --from=stage-compile-sources /opencascade.js/build/sources /opencascade.js/build/sources
COPY --from=stage-bindgen /opencascade.js/build/bindings /opencascade.js/build/bindings
COPY src/build_yaml.py /opencascade.js/src/build_yaml.py

WORKDIR /opencascade.js/src/

ENTRYPOINT ["uv", "run", "build_yaml.py"]
