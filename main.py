import os
import sys

# Ensure project root is in sys.path
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.desktop.bridge import launch_liquid_studio


def main():
    launch_liquid_studio()


if __name__ == "__main__":
    main()
