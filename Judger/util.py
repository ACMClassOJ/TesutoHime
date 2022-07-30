import os.path
from config import working_dir

def work_file(filename: str) -> str:
    return os.path.join(working_dir, filename)
