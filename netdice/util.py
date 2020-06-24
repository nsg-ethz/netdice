import os

project_root_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))


def get_relative_to_working_directory(file: str):
    return os.path.abspath(os.path.join(os.getcwd(), file))
