import os
import sys
import pathlib
from typing import NoReturn

THIS_FILE_PATH: pathlib.Path = pathlib.Path(__file__).resolve()
NBS_DIR: pathlib.Path = THIS_FILE_PATH.parent
REPO_DIR: pathlib.Path = NBS_DIR.parent
DJANGO_BASE_DIR: pathlib.Path = REPO_DIR / "src"


def init_django(project_name: str = 'tradr') -> NoReturn:
    """Run administrative tasks."""
    os.chdir(DJANGO_BASE_DIR)
    sys.path.insert(0, str(DJANGO_BASE_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"{project_name}.settings")
    os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = "true"
    import django
    django.setup()
