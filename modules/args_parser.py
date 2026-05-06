# modules/args_parser.py
import argparse

def parse_args(argv):
    parser = argparse.ArgumentParser(description="IDM Activation Script")
    parser.add_argument("/act", action="store_true", help="Activate IDM")
    parser.add_argument("/frz", action="store_true", help="Freeze trial period")
    parser.add_argument("/res", action="store_true", help="Reset activation / trial")
    args = parser.parse_args(argv)

    return {
        "activate": args.act,
        "freeze": args.frz,
        "reset": args.res
    }
