import clang.cindex

from common import includePathArgs, occtBasePath, ocIncludeStatements
from filters.filterEnums import filterEnum
from filters.filterTypedefs import filterTypedef
from wasmGenerator.common import ignoreDuplicateTypedef


def parse(additionalCppCode = ""):
  index = clang.cindex.Index.create()
  translationUnit = index.parse(
    "myMain.h", [
      "-x",
      "c++",
      "-stdlib=libc++",
      "-D__EMSCRIPTEN__"
    ] + includePathArgs,
    [["myMain.h", ocIncludeStatements + "\n" + additionalCppCode]]
  )

  if len(translationUnit.diagnostics) > 0:
    print("Diagnostic Messages:")
    for d in translationUnit.diagnostics:
      print("  " + d.format())

  return translationUnit

def templateTypedefGenerator(tu):
  return list(filter(
    lambda x:
      x.kind == clang.cindex.CursorKind.TYPEDEF_DECL and
      not (x.get_definition() is None or not x == x.get_definition()) and
      filterTypedef(x) and
      x.type.get_num_template_arguments() != -1 and
      not ignoreDuplicateTypedef(x),
    tu.cursor.get_children()))

def typedefGenerator(tu):
  return list(filter(lambda x: x.kind == clang.cindex.CursorKind.TYPEDEF_DECL, tu.cursor.get_children()))

def allChildrenGenerator(tu):
  return list(tu.cursor.get_children())

def enumGenerator(tu):
  return list(filter(lambda x: x.kind == clang.cindex.CursorKind.ENUM_DECL and filterEnum(x), tu.cursor.get_children()))

def classDict(tu):
  d = dict()
  for x in tu.cursor.get_children():
    if (
      x.kind == clang.cindex.CursorKind.CLASS_DECL or
      x.kind == clang.cindex.CursorKind.STRUCT_DECL
    ) and not (
      x.get_definition() is None or
      not x == x.get_definition()
    ):
      if x.spelling not in d:
        # Original code didn't handle duplicate names, that seems bad?
        d[x.spelling] = x
  return d

def underlyingDict(l, checkOcctBasePath: bool):
  d = dict()
  for x in l:
    if checkOcctBasePath and not x.location.file.name.startswith(occtBasePath):
      continue
    if x.underlying_typedef_type.spelling not in d:
      # Original code didn't handle duplicate names, that seems bad?
      d[x.underlying_typedef_type.spelling] = x
  return d


class TuInfo:
  """Utility class for tracking information about a Translation Unit"""
  def __init__(self, customCode: str):
    self.tu = parse(customCode)
    """The loaded clang Translation Unit"""
    self.allChildren = allChildrenGenerator(self.tu)
    self.typedefs = typedefGenerator(self.tu)
    self.enums = enumGenerator(self.tu)
    self.templateTypedefs = templateTypedefGenerator(self.tu)
    self.classDict = classDict(self.tu)
    self.typedefUnderlyingDict = underlyingDict(self.typedefs, True)
    self.templateTypedefUnderlyingDict = underlyingDict(self.templateTypedefs, False)
