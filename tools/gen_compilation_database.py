#!/usr/bin/env python3

import argparse
import glob
import json
import logging
import os
import shlex
import subprocess
from pathlib import Path


def runBazelBuildForCompilationDatabase(bazel_options, bazel_targets):
  query_targets = ' union '.join(bazel_targets)
  query = ' union '.join(
      q.format(query_targets) for q in [
          'attr(include_prefix, ".+", kind(cc_library, deps({})))',
          'attr(strip_include_prefix, ".+", kind(cc_library, deps({})))',
          'attr(generator_function, ".*proto_library", kind(cc_.*, deps({})))',
      ])
  build_targets = subprocess.check_output(["bazel", "query", "--notool_deps",
                                           query]).decode().splitlines()
  subprocess.check_call(["bazel", "build"] + bazel_options + build_targets)


# This method is equivalent to https://github.com/grailbio/bazel-compilation-database/blob/master/generate.sh
def generateCompilationDatabase(args):
  # We need to download all remote outputs for generated source code. This option lives here to override those
  # specified in bazelrc.
  bazel_options = shlex.split(os.environ.get("BAZEL_BUILD_OPTIONS", "")) + [
      "--config=compdb",
      "--remote_download_outputs=all",
  ]
  if args.keep_going:
    bazel_options.append("-k")
  if args.run_bazel_build:
    try:
      runBazelBuildForCompilationDatabase(bazel_options, args.bazel_targets)
    except subprocess.CalledProcessError as e:
      if not args.keep_going:
        raise
      else:
        logging.warning("bazel build failed {}: {}".format(e.returncode, e.cmd))

  subprocess.check_call(["bazel", "build"] + bazel_options + [
      "--aspects=@bazel_compdb//:aspects.bzl%compilation_database_aspect",
      "--output_groups=compdb_files"
  ] + args.bazel_targets)

  execroot = subprocess.check_output(["bazel", "info", "execution_root"] +
                                     bazel_options).decode().strip()

  compdb = []
  for compdb_file in Path(execroot).glob("**/*.compile_commands.json"):
    compdb.extend(json.loads("[" + compdb_file.read_text().replace("__EXEC_ROOT__", execroot) +
                             "]"))
  return compdb


def isHeader(filename):
  for ext in (".h", ".hh", ".hpp", ".hxx"):
    if filename.endswith(ext):
      return True
  return False


def isCompileTarget(target, args):
  filename = target["file"]
  if not args.include_headers and isHeader(filename):
    return False

  if not args.include_genfiles:
    if filename.startswith("bazel-out/"):
      return False

  if not args.include_external:
    if filename.startswith("external/"):
      return False

  return True


def modifyCompileCommand(target, args):
  cc, options = target["command"].split(" ", 1)

  # Workaround for bazel added C++11 options, those doesn't affect build itself but
  # clang-tidy will misinterpret them.
  options = options.replace("-std=c++0x ", "")
  options = options.replace("-std=c++11 ", "")

  if args.vscode:
    # Visual Studio Code doesn't seem to like "-iquote". Replace it with
    # old-style "-I".
    options = options.replace("-iquote ", "-I ")

  if isHeader(target["file"]):
    options += " -Wno-pragma-once-outside-header -Wno-unused-const-variable"
    options += " -Wno-unused-function"

  target["command"] = " ".join([cc, options])
  return target


def fixCompilationDatabase(args, db):
  db = [modifyCompileCommand(target, args) for target in db if isCompileTarget(target, args)]

  with open("compile_commands.json", "w") as db_file:
    json.dump(db, db_file, indent=2)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Generate JSON compilation database')
  parser.add_argument('--run_bazel_build', action='store_true')
  parser.add_argument('-k', '--keep_going', action='store_true')
  parser.add_argument('--include_external', action='store_true')
  parser.add_argument('--include_genfiles', action='store_true')
  parser.add_argument('--include_headers', action='store_true')
  parser.add_argument('--vscode', action='store_true')
  parser.add_argument('bazel_targets',
                      nargs='*',
                      default=["//source/...", "//test/...", "//tools/..."])
  args = parser.parse_args()
  fixCompilationDatabase(args, generateCompilationDatabase(args))
