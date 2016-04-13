import sys
import os



def normalize_path(path):
    return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
