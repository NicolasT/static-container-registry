#!/bin/sh

set -ue

python3 /static_container_registry.py /var/lib/images > /var/run/static-container-registry.conf

exec "$@"
