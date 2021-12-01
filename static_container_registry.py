#!/usr/bin/env python

# pylint: disable=consider-using-f-string
""" Script to generate nginx configuration to serve as container registry. """

import sys
import os.path
import json
import hashlib
import logging
import argparse


LOGGER = logging.getLogger(__name__)


CONSTANTS = '''
location = /v2 {{
    return 301 /v2/;
}}

location = /v2/ {{
    return 200 'ok';
}}

location @404_tag {{
    internal;
    types {{ }} default_type "application/json";
    return 404 '{tag_invalid:s}';
}}
'''.format(
        tag_invalid=json.dumps({
            'errors': [{
                'code': 'TAG_INVALID',
                'message': 'manifest tag did not match URI',
                'detail': '',
            }]
        }),
    )


MANIFEST_JSON = 'manifest.json'


def find_images(root):
    """ Find list of images in the specified root folder. """
    LOGGER.info('Finding images in %s', root)

    for name in os.listdir(root):
        curr = os.path.join(root, name)
        LOGGER.info('Looking into %s for tags of %s', curr, name)

        if not os.path.isdir(curr):
            continue

        for tag in os.listdir(curr):
            curr = os.path.join(root, name, tag)

            if not os.path.isdir(curr):
                LOGGER.info('Not a directory: %s', curr)
                continue

            LOGGER.info('Looking into %s for a valid image', curr)

            manifest = os.path.join(curr, MANIFEST_JSON)

            if not os.path.isfile(manifest):
                LOGGER.info('No manifest file at %s', manifest)
                continue

            with open(manifest, 'r', encoding='utf-8') as file:
                LOGGER.info('Attempting to load JSON data from %s', manifest)
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    LOGGER.info('Failed to decode JSON from %s', manifest)
                    data = None

            if not data:
                continue

            if data.get('schemaVersion') != 2:
                LOGGER.info('Invalid schemaVersion in %s', manifest)
                continue

            media_type = data.get('mediaType')
            if not media_type in [
                    'application/vnd.docker.distribution.manifest.v2+json',
                    'application/vnd.oci.image.manifest.v1+json']:
                LOGGER.info('Invalid mediaType in %s : %s', manifest, media_type)
                continue

            LOGGER.info('Found image %s:%s in %s', name, tag, curr)
            yield (name, tag, media_type)


def compute_digest(filename):
    """ Compute file digest. """
    digest = hashlib.sha256()
    with open(filename, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b''):
            digest.update(chunk)
    return digest.hexdigest()


def create_config(root, server_root, name_prefix, with_constants=True,
                  only_constants=False):
    """ Create nginx configuration snippets for the images in folder. """
    if with_constants:
        yield CONSTANTS

    if only_constants:
        return

    images = {}
    for (name, tag, media_type) in find_images(root):
        images.setdefault(name, {})[tag] = media_type

    for (name, tags) in sorted(images.items()):
        tag_list = {
            'name': name,
            'tags': sorted(tags.keys()),
        }

        yield '''
location = /v2/{name_prefix:s}{name:s}/tags/list {{
    types {{ }} default_type "application/json";
    return 200 '{payload:s}';
}}
'''.format(
        name=name,
        name_prefix=name_prefix.lstrip('/'),
        payload=json.dumps(tag_list),
    )

        seen_digests = set()

        for (tag, media_type) in sorted(tags.items()):
            hexdigest = compute_digest(os.path.join(root, name, tag, MANIFEST_JSON))

            yield '''
location = "/v2/{name_prefix:s}{name:s}/manifests/{tag:s}" {{
    alias {server_root:s}/{name:s}/{tag:s}/;
    types {{ }} default_type "{media_type:s}";
    add_header 'Docker-Content-Digest' 'sha256:{digest:s}';
    try_files manifest.json =404;
    error_page 404 @404_tag;
}}
'''.format(
        name=name,
        tag=tag,
        media_type=media_type,
        name_prefix=name_prefix.lstrip('/'),
        digest=hexdigest,
        server_root=server_root,
    )

            if hexdigest not in seen_digests:
                yield '''
location = "/v2/{name_prefix:s}{name:s}/manifests/sha256:{digest:s}" {{
    alias {server_root:s}/{name:s}/{tag:s}/;
    types {{ }} default_type "{media_type:s}";
    add_header 'Docker-Content-Digest' 'sha256:{digest:s}';
    try_files manifest.json =404;
    error_page 404 @404_tag;
}}
'''.format(
        name=name,
        tag=tag,
        media_type=media_type,
        name_prefix=name_prefix.lstrip('/'),
        digest=hexdigest,
        server_root=server_root,
    )
            else:
                yield '''
# Digest for "{name:s}:{tag:s}" already served
'''.format(
        name=name,
        tag=tag,
    )

            seen_digests.add(hexdigest)

        yield '''
location ~ "/v2/{name_prefix:s}{name:s}/blobs/sha256:([a-f0-9]{{64}})" {{
    alias {server_root:s}/{name:s}/;
    try_files {paths:s} =404;
}}
'''.format(
        name_prefix=name_prefix.lstrip('/'),
        server_root=server_root,
        name=name,
        paths=' '.join('{tag:s}/$1'.format(tag=tag) for tag in sorted(tags.keys())),
    )


def main():
    """ Main entrypoint. """
    logging.basicConfig(
        level=logging.INFO,
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--name-prefix',
        metavar='PREFIX',
        help='optional prefix added to every image name',
    )

    constants_group = parser.add_mutually_exclusive_group()
    constants_group.add_argument(
        '--omit-constants',
        action='store_true',
        help='do not write rules for constant locations (e.g. /v2/),'
                ' necessary to include the configuration with others.',
    )
    constants_group.add_argument(
        '--only-constants',
        action='store_true',
        help='only write rules for constant locations (e.g. /v2/),'
                ' to include only once.',
    )

    root = os.getcwd()
    parser.add_argument(
        '--server-root',
        metavar='PATH',
        help='root directory from where exported image files are served' \
                ' (default: ROOT)'
    )
    parser.add_argument(
        'root',
        metavar='ROOT',
        nargs='?',
        default=root,
        help='root directory containing exported images (default: {})'.format(
                root),
    )

    args = parser.parse_args()

    name_prefix = '{}/'.format((args.name_prefix or '').strip('/'))
    with_constants = not args.omit_constants
    only_constants = args.only_constants
    root = os.path.abspath(args.root)
    server_root = args.server_root or root

    logging.debug('Name prefix: %s', name_prefix)
    logging.debug('Server root: %s', server_root)
    logging.debug('Root: %s', root)

    config_gen = create_config(
        root, server_root, name_prefix, with_constants, only_constants
    )
    for part in config_gen:
        sys.stdout.write(part)


if __name__ == '__main__':
    main()
