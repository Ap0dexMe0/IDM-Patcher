import sys
import subprocess
import os
from modules.args_parser import parse_args
from modules.idm import (
    is_admin, elevate, check_idm_installed, reset_activation, activate_idm,
    freeze_trial, show_main_menu
)

def main():
    args = parse_args(sys.argv[1:])

    # Re-launch with admin rights if needed
    if not is_admin():
        elevate()
        return

    # Perform requested actions
    if args['reset']:
        reset_activation()
    elif args['activate']:
        activate_idm()
    elif args['freeze']:
        freeze_trial()
    else:
        show_main_menu()

if __name__ == "__main__":
    main()
