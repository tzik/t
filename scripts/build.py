
import json
import os
import re
import shlex
import sys

from util import launchers, ancestors, run, git


ninja_env = {
    'NINJA_STATUS': '[%u/%r/%f] '
}


def setup_subcommand(subparsers):
    parser_build = subparsers.add_parser('build')
    parser_build.set_defaults(handler=cmd_build)
    parser_build.add_argument('srcs', nargs='*')


def attempt_compdb(args, wd, key_file):
    if len(args.srcs) == 0:
        return False

    srcs = {os.path.abspath(src) for src in args.srcs}

    with open(key_file, encoding='utf-8') as fd:
        compdb = json.load(fd)
    for entry in compdb:
        cwd = entry['directory']
        path = os.path.normpath(os.path.join(cwd, entry['file']))
        if path not in srcs:
            continue
        srcs.remove(path)

        if 'arguments' in entry:
            cmd = entry['arguments']
        else:
            cmd = shlex.split(entry['command'])
        print(f't build: Entering directory `{cwd}\'')
        run(launchers + cmd, cwd=cwd)
    return len(srcs) == 0


def attempt_ninja(args, wd, key_file):
    targets = [os.path.abspath(src) + '^' for src in args.srcs]
    run(launchers + ['ninja', '-C',
                     os.path.dirname(key_file)] + targets,
        env=ninja_env)
    return True


def attempt_make(args, wd, key_file):
    run(launchers + ['make', '-C', os.path.dirname(key_file)])
    return True


cmake_proj_pattern = re.compile('^\\W*project\\W*\\(')


def is_cmake_proj_root(cmake_file):
    with open(cmake_file, encoding='utf-8') as fd:
        for line in fd.readlines():
            if cmake_proj_pattern.match(line):
                return True
    return False


def attempt_cmake(args, wd, key_file):
    if not is_cmake_proj_root(key_file):
        return False

    src_dir = os.path.dirname(key_file)
    build_dir = os.path.join(src_dir, 'build')
    out_dir = os.path.join(src_dir, 'out')

    cflags = [
        '-ffunction-sections',
        '-fdata-sections',
        '-ffile-compilation-dir=.',
        '-march=native',
        '-Wall', '-Wextra', '-pedantic', '-Werror',
        '-Wglobal-constructors',
        '-Wexit-time-destructors',
    ]

    cflags_debug = [
        '-g',
        '-fsanitize=address',
    ]

    cxxflags = [
        '-fno-rtti',
    ]

    ldflags = [
        '-Wl,--gc-sections',
        '-Wl,--icf=all',
        '-Wl,--fatal-warnings',
    ]

    run(launchers + [
        'cmake',
        '--fresh',
        '-G', 'Ninja',
        '-Wdev', '-Werror=dev',
        '-Wdeprecated', '-Werror=deprecated',
        '-S', src_dir,
        '-B', build_dir,
        '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
        '-DCMAKE_INSTALL_PREFIX=' + out_dir,
        '-DCMAKE_INSTALL_RPATH=$ORIGIN/../lib',
        '-DCMAKE_INSTALL_LIBDIR=lib',

        '-DBUILD_SHARED_LIBS=ON',
        '-DCMAKE_POSITION_INDEPENDENT_CODE=ON',

        '-DCMAKE_BUILD_TYPE=RelWithDebInfo',

        '-DCMAKE_C_COMPILER=clang',
        '-DCMAKE_C_FLAGS=' + shlex.join(cflags),
        '-DCMAKE_C_COMPILER_LAUNCHER=ccache',
        '-DCMAKE_C_FLAGS_DEBUG=' + shlex.join(cflags_debug),

        '-DCMAKE_CXX_COMPILER=clang++',
        '-DCMAKE_CXX_FLAGS=' + shlex.join(cflags + cxxflags),
        '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
        '-DCMAKE_CXX_FLAGS_DEBUG=' + shlex.join(cflags_debug),

        '-DCMAKE_SHARED_LINKER_FLAGS=' + shlex.join(ldflags),
        '-DCMAKE_EXE_LINKER_FLAGS=' + shlex.join(ldflags),
    ])

    run(launchers + [
        'cmake', '--build', build_dir
    ])

    # run(launchers + [
    #     'cmake', '--install', build_dir
    # ])

    return True


build_handlers = [
    ['build/compile_commands.json', attempt_compdb],
    ['build/build.ninja', attempt_ninja],
    ['build.ninja', attempt_ninja],
    ['build/Makefile', attempt_make],
    ['Makefile', attempt_make],
    ['CMakeLists.txt', attempt_cmake],
]


def cmd_build(args):
    top_dir = git(['rev-parse', '--show-cdup'])
    cmd = git(['config', 'build.command'])
    if top_dir is not None and cmd is not None:
        run(shlex.split(cmd), cwd=os.path.abspath(top_dir))
        sys.exit(0)

    for wd in ancestors(os.getcwd()):
        for key_file_rel, handler in build_handlers:
            key_file = os.path.join(wd, key_file_rel)
            if os.path.exists(key_file) and handler(args, wd, key_file):
                sys.exit(0)
    sys.exit(1)
