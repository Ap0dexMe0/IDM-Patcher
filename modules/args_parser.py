# modules/args_parser.py
import argparse

def parse_args(argv):
    parser = argparse.ArgumentParser(description="IDM Activation Script")
    parser.add_argument("--active", action="store_true", help="Activate IDM")
    parser.add_argument("--freeze", action="store_true", help="Freeze trial period")
    parser.add_argument("--reset", action="store_true", help="Reset activation / trial")
    args = parser.parse_args(argv)

    return {
        "activate": args.active,
        "freeze": args.freeze,
        "reset": args.reset
    }
