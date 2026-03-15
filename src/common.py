import os

from filters.includes import filter_include

OCCT_SRC_PATH = "/occt/src/"


def as_include_args(paths: list[str]) -> list[str]:
    return [f"-I{path}" for path in paths]


def get_global_includes() -> tuple[
    list[str], list[str], list[str], dict[str, int], dict[str, int]
]:
    include_files: list[str] = []
    include_paths: list[str] = []
    source_files: list[str] = []

    source_map: dict[str, int] = {}
    include_map: dict[str, int] = {}

    for dirpath, _, filenames in os.walk(OCCT_SRC_PATH):
        include_paths.append(dirpath)
        for item in filenames:
            file = os.path.join(dirpath, item)  # e.g., /occt/src/AIS/AIS.hxx

            header_variant = item.replace(".cxx", ".hxx")
            source_variant = item.replace(".hxx", ".cxx")
            if item.endswith(".cxx") and filter_include(header_variant):
                source_files.append(file)
                source_map[source_variant] = 1

            elif item.endswith(".hxx") and filter_include(item):
                include_files.append(file)
                if source_variant not in filenames: # in case we reach the header variant first
                    include_map[header_variant] = 1

    return (
        sorted(include_files),
        sorted(include_paths),
        sorted(source_files),
        source_map,
        include_map,
    )


[
    OCCT_INCLUDE_FILES,
    OCCT_INCLUDE_PATHS,
    OCCT_SOURCE_FILES,
    OCCT_SOURCE_MAP,
    OCCT_INCLUDE_MAP,
] = get_global_includes()

def resolve_header_source(header_or_source_path: str) -> str:
    """Gets the source file of the given header filepath. If no source file is found, try to fallback to the header file. If neither is found, throw."""
    if not header_or_source_path.startswith(OCCT_SRC_PATH):
        raise
    source_variant = header_or_source_path.replace(".hxx", ".cxx")
    header_variant = header_or_source_path.replace(".cxx", ".hxx")
    if source_variant in OCCT_SOURCE_MAP:
        return source_variant
    elif header_variant in OCCT_INCLUDE_MAP:
        return header_variant
    else:
        raise
    

OCCT_INCLUDE_PATH_ARGS = as_include_args(OCCT_INCLUDE_PATHS)

_3RD_PARTY_INCLUDES = [
    "/rapidjson/include",
]

OCCT_INCLUDE_PATHS_WITH_3RD_PARTY = OCCT_INCLUDE_PATHS + _3RD_PARTY_INCLUDES
OCCT_INCLUDE_PATH_ARGS_WITH_3RD_PARTY = as_include_args(
    OCCT_INCLUDE_PATHS_WITH_3RD_PARTY
)

EMSDK_INCLUDES = [
    "/emsdk/upstream/emscripten/system/include/",
    "/usr/lib/gcc/x86_64-linux-gnu/8/include-fixed/",
    "/emsdk/upstream/emscripten/system/lib/libcxx/include/",
    "/emsdk/upstream/emscripten/cache/sysroot/include/",
    f"/emsdk/upstream/lib/clang/{next(os.walk('/emsdk/upstream/lib/clang/'))[1][0]}/include/",
    "/emsdk/upstream/emscripten/system/lib/libcxx/include/__support/newlib/",
]

EMCC_INCLUDE_PATH_ARGS = as_include_args(
    EMSDK_INCLUDES + OCCT_INCLUDE_PATHS_WITH_3RD_PARTY
)

ALL_OCCT_INCLUDE_STATEMENTS = (
    os.linesep.join([f'#include "{os.path.basename(x)}"' for x in OCCT_INCLUDE_FILES])
    + os.linesep
)
