# -- coding: utf-8 --

import os
import pwd
import grp
import json
from os import getenv
from socket import gethostname
from client import caller


## Gather and map information
#TODO: Run state to check and verify system current state

# Base dir / root of git repository
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Hostname
hostname = gethostname()

# User details
user = 'mox'
group = 'mox'

# Virtual environment and python executable
virtualenv = getenv("VIRTUALENV")
python_exec = getenv("PYTHON_EXEC")

# Create config
db_config = {
    "host": "localhost",
    "name": "mox",
    "user": "mox",
    "pass": "mox",
    "superuser": "postgres"
}

mox_config = {
    "hostname": hostname,
    "user": user,
    "group": group,
    "base_dir": base_dir,
    "virtualenv": virtualenv,
    "python_exec": python_exec,
    "db": db_config,
    "http_port": 80,
    "https_port": 443,
    "ssl_certificate": None,
    "ssl_certificate_key": None,
}

# Set grains (configuration)
# grains.setval key value
set_grains = caller.cmd("grains.setval", "mox_config", mox_config)

formatted = json.dumps(set_grains, indent=2, sort_keys=True)

print("""
Set grain/system values for the installation process

{grains}
""".format(grains=formatted))
