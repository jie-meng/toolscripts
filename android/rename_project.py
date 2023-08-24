# coding: utf-8

import click
import os
import shutil
from typing import List, Final
from functools import partial
from binaryornot.check import is_binary

TEMP_FOLDER: Final = '.temp'

def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)

def read_gitignore_entries() -> List[str]:
    gitignore_path = os.path.join(os.getcwd(), '.gitignore')

    if not os.path.exists(gitignore_path):
        return []

    with open(gitignore_path, 'r', encoding='utf-8', errors='replace') as f:
        return [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]

def is_ignored(path: str, ignored_entries: List[str]) -> bool:
    if '.git' in path:
        return True
    #  bug in ignore_entries, need further test
    #  for entry in ignored_entries:
    #      if os.path.commonpath([path, entry]) == entry:
    #          return True
    return False

def find_files_recursively(path: str, pred=None, ls=None, ignored_entries=None) -> List[str]:
    if ls is None:
        ls = []

    if not os.path.isdir(path):
        return ls

    for p in os.listdir(path):
        p = os.path.join(path, p)
        if is_ignored(p, ignored_entries):
            continue
        if os.path.isdir(p):
            find_files_recursively(p, pred, ls, ignored_entries)
        elif os.path.isfile(p):
            if not pred or pred(p):
                ls.append(p)

    return ls

def find_dirs_recursively(path: str, pred=None, ls=None, ignored_entries=None) -> List[str]:
    if ls is None:
        ls = []

    if not os.path.isdir(path):
        return ls

    for p in os.listdir(path):
        p = os.path.join(path, p)
        if is_ignored(p, ignored_entries):
            continue
        if os.path.isdir(p):
            if not pred or pred(p):
                ls.append(p)
            find_dirs_recursively(p, pred, ls, ignored_entries)

    return ls

def read_text_file(file: str) -> str:
    with open(file, mode='r', encoding='utf-8', errors='replace') as f:
       return f.read()

def write_text_file(file: str, content: str):
    with open(file, mode='w', encoding='utf-8') as f:
       f.write(content)

def update_dir_tree(dir: str, src_part: str, dst_part: str) -> str:
    base_path = rreplace(dir, os.path.sep + src_part, '', 1)
    src_part_prefix = src_part.split(os.path.sep)[0]

    temp_dir = os.path.join(os.getcwd(), TEMP_FOLDER)

    shutil.rmtree(temp_dir, True)
    shutil.move(dir, temp_dir)
    shutil.rmtree(os.path.join(base_path, src_part_prefix), True)
    shutil.move(temp_dir, os.path.join(base_path, dst_part))
    shutil.rmtree(temp_dir, True)

def on_walk_project_file_android(file: str, old_package: str, new_package: str):
    if not is_binary(file):
        text = read_text_file(file)
        text = text.replace(old_package, new_package)
        text = text.replace(old_package.replace('.', os.path.sep), new_package.replace('.', os.path.sep))
        write_text_file(file, text)
        return True

def on_walk_project_dir(dir: str, old_package: str, new_package: str):
    old_package_path = old_package.replace('.', os.path.sep)
    if dir.endswith(old_package_path):
        update_dir_tree(dir, old_package_path, new_package.replace('.', os.path.sep))
        return True

@click.command()
@click.option('--old_package', prompt='old package', required=True, help='Old package')
@click.option('--new_package', prompt='new package', required=True, help='New package')
def process_android_project(old_package, new_package):
    ignored_entries = read_gitignore_entries()

    find_files_recursively(os.getcwd(), partial(on_walk_project_file_android, old_package=old_package, new_package=new_package), ignored_entries=ignored_entries)
    find_dirs_recursively(os.getcwd(), partial(on_walk_project_dir, old_package=old_package, new_package=new_package), ignored_entries=ignored_entries)

    click.echo('\nDone!')

if __name__ == '__main__':
    process_android_project()

