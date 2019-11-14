# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import base64

from google.cloud import kms_v1

def _decrypt(client, key_path, content):
  """_decrypt deciphers credentials from base64 by KMS's symetric CryptoKey."""

  response = client.decrypt(key_path, base64.b64decode(content))
  return response.plaintext


def _encrypt(client, key_path, content):
  """_encrypt encodes the credentials to base64 by KMS's symetric CryptoKey."""

  response = client.encrypt(key_path, content)
  return base64.b64encode(response.ciphertext)


def main():
  """The main function to transfer plain text to/from cipher."""

  parser = argparse.ArgumentParser(description='A helper to decode or encode'
                                   'the credentials of ci_results_archiver')
  parser.add_argument('action', choices=['cipher', 'decipher'],
                      help='cipher or decipher')
  parser.add_argument('text', metavar='STRING',
                      help='text to cipher or decipher')
  parser.add_argument('--project', default='cros-test-platform-kms',
                      help='project id')
  parser.add_argument('--location', default='global',
                      help='location to store the key')
  parser.add_argument('--key_ring', default='ci_results_archiver',
                      help='key ring name')
  parser.add_argument('--key_id', default='mysql_wrapper', help='key name')
  args = parser.parse_args()

  client = kms_v1.KeyManagementServiceClient()
  key_path = client.crypto_key_path_path(args.project,
                                         args.location,
                                         args.key_ring,
                                         args.key_id)
  if args.action == 'cipher':
    print(_encrypt(client, key_path, args.text))
  if args.action == 'decipher':
    print(_decrypt(client, key_path, args.text))


if __name__ == '__main__':
  main()
