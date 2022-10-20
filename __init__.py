import sys
import pathlib

thirdparty_dir = pathlib.Path(__file__).parent.absolute() / "thirdparty"
for addon in ["kyujipy", "pycson", "speg"]:
    sys.path.append(str(thirdparty_dir / addon))

from .hanziweb import init as hanziweb_init  # noqa
from .jitai import init as jitai_init  # noqa

hanziweb_init()
jitai_init()
