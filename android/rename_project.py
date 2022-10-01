# coding: utf-8

import click
import os
import shutil
from typing import List, Final
from functools import partial
from binaryornot.check import is_binary

PATH_SEP = '/'
TEMP_FOLDER: Final = '.temp'

def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)

def find_files_recursively(path: str, pred = None, ls = None) -> List[str]:
    if ls == None:
        ls = []

    if not os.path.isdir(path):
        return ls

    for p in os.listdir(path):
        p = os.path.join(path, p)
        if os.path.isdir(p):
            find_files_recursively(p, pred, ls)
        elif os.path.isfile(p):
            if not pred or pred(p):
                ls.append(p)

    return ls


def find_dirs_recursively(path: str, pred = None, ls = None) -> List[str]:
    if ls == None:
        ls = []

    if not os.path.isdir(path):
        return ls

    for p in os.listdir(path):
        p = os.path.join(path, p)
        if os.path.isdir(p):
            if not pred or pred(p):
                ls.append(p)

            find_dirs_recursively(p, pred, ls)

    return ls


def read_text_file(file: str) -> str:
    with open(file, mode = 'r') as f:
       return f.read()


def write_text_file(file: str, content: str) -> str:
    with open(file, mode = 'w') as f:
       return f.write(content)


def update_dir_tree(dir: str, src_part: str, dst_part: str) -> str:
    base_path = rreplace(dir, PATH_SEP + src_part, '', 1)
    src_part_prefix = src_part.split(PATH_SEP)[0]

    temp_dir = os.getcwd() + PATH_SEP + TEMP_FOLDER

    shutil.rmtree(temp_dir, True)
    shutil.move(dir, temp_dir)
    shutil.rmtree(base_path + PATH_SEP + src_part_prefix, True)
    shutil.move(temp_dir, base_path + PATH_SEP + dst_part)
    shutil.rmtree(temp_dir, True)


def on_walk_project_file_android(file: str, old_package: str, new_package: str):
    if not is_binary(file):
        text = read_text_file(file)
        text = text.replace(old_package, new_package)
        text = text.replace(old_package.replace('.', PATH_SEP), new_package.replace('.', PATH_SEP))
        write_text_file(file, text)

        return True

def on_walk_project_dir(dir: str, old_package: str, new_package: str):
    old_package_path = old_package.replace('.', PATH_SEP)
    if dir.endswith(old_package_path):
        update_dir_tree(dir, old_package_path, new_package.replace('.', PATH_SEP))

        return True


@click.command()
@click.option('--old_package', prompt = 'old package', required = True, help = 'Old package')
@click.option('--new_package', prompt = 'new package', required = True, help = 'New package')
def process_android_project(old_package, new_package):
    """Rename android project"""
    # walk all text file and replace package
    find_files_recursively(os.getcwd(), partial(on_walk_project_file_android, old_package = old_package, new_package = new_package))

    # walk all dirs end with ark package
    find_dirs_recursively(os.getcwd(), partial(on_walk_project_dir, old_package = old_package, new_package = new_package))

    click.echo('\nDone!')

if __name__ == '__main__':
    process_android_project()

