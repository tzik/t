
import argparse

import build


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    build.setup_subcommand(subparsers)

    args = parser.parse_args()
    if hasattr(args, 'handler'):
        args.handler(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
