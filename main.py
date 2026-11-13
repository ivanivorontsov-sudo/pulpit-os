"""Точка входа Пульта."""

import multiprocessing
import sys

from pulpit.shell import main


if __name__ == "__main__":
    multiprocessing.freeze_support()
    if "--site-builder" in sys.argv[1:]:
        from pulpit.builder_app import run

        run()
    else:
        main()
