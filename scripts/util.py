
import os
import shlex
import subprocess
import termcolor


prompt = termcolor.colored('$', 'blue', attrs=['bold'])
launchers = [
    'nice', '-n19', '--',
    'ionice', '-c3', '--',
    'choom', '-n1000', '--',
]


def ancestors(path):
    while True:
        yield path
        parent = os.path.dirname(path)
        if parent == path:
            return
        path = parent


def apply_env(env):
    if env is None:
        return env
    res = os.environ.copy()
    res.update(env)
    return res


def run(cmd, **kwargs):
    cmd_print = []
    if 'cwd' in kwargs:
        cmd_print += ['-C', kwargs['cwd']]
    if 'env' in kwargs:
        cmd_print += [key + '=' + value
                      for key, value in kwargs['env'].items()]
    if len(cmd_print) > 0:
        cmd_print = ['env'] + cmd_print + ['--']
    print(prompt + shlex.join(cmd_print + cmd))

    if 'env' in kwargs:
        kwargs['env'] = apply_env(kwargs['env'])
    if 'check' not in kwargs:
        kwargs['check'] = True
    return subprocess.run(cmd, **kwargs)


def git(cmd, git_dir=None):
    alt_git_dir = ['--git-dir=' + git_dir] if git_dir is not None else []
    rv = run(['git'] + alt_git_dir + cmd,
             check=False, stdout=subprocess.PIPE)
    if rv.returncode != 0:
        return None
    return rv.stdout.decode().rstrip()
