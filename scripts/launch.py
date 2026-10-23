"""PyInstaller entry point; guarded for Windows multiprocessing spawn."""
import multiprocessing
from graphmath.app.main import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
