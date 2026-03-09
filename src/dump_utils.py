import clang.cindex
from common import ocIncludePaths


def get_oc_includes(path: str):
    index = clang.cindex.Index.create()
    translation_unit = index.parse(
        path,
        ["-x", "c++", "-stdlib=libc++", "-d__emscripten__"]
        + list(map(lambda p: "-I" + p, ocIncludePaths)),
    )
    return translation_unit.get_includes()
