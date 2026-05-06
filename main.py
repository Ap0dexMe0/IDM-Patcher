import sys
import subprocess
import os
from modules.args_parser import parse_args
from modules.idm import (
    reset_activation, activate_idm, freeze_trial
)

def main():
    args = parse_args(sys.argv[1:])

    # Perform requested actions
    if args['reset']:
        reset_activation()
    elif args['activate']:
        activate_idm()
    elif args['freeze']:
        freeze_trial()
    else:
        print("No action specified. Use --active, --freeze, or --reset")
        print("Run 'main.py --help' for more information.")

if __name__ == "__main__":
    main()
