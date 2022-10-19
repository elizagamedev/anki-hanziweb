import sys
import pathlib

thirdparty_dir = pathlib.Path(__file__).parent.absolute() / "thirdparty"
for addon in ["kyujipy", "pycson", "speg"]:
    sys.path.append(str(thirdparty_dir / addon))

from .main import main  # noqa

main()
