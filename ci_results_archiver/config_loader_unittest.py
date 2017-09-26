# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for config_loader."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import contextlib
import os
import shutil
import tempfile
import unittest

import yaml

from ci_results_archiver import config_loader


class ConfigLoaderTestCase(unittest.TestCase):
  """Unit tests for config_loader."""

  def testLoad(self):
    """Loads a file with !import directive."""
    with _TemporaryDirectory() as temp_dir:
      with open(os.path.join(temp_dir, 'config.yaml'), 'w') as f:
        f.write("""
          test:
            credentials: !import "./creds.yaml"
            timezone: "US/Pacific"
        """)
      with open(os.path.join(temp_dir, 'creds.yaml'), 'w') as f:
        f.write("""
          username: "kitten"
          password: "meow"
        """)
      configs = config_loader.Load(os.path.join(temp_dir, 'config.yaml'))
      self.assertEquals({
          'test': {
              'credentials': {
                  'username': 'kitten',
                  'password': 'meow',
              },
              'timezone': 'US/Pacific',
          },
      }, configs)

  def testMissingImport(self):
    """Loads a file with missing !import."""
    with _TemporaryDirectory() as temp_dir:
      with open(os.path.join(temp_dir, 'config.yaml'), 'w') as f:
        f.write("""
          test:
            credentials: !import "./no_such_file.yaml"
            timezone: "US/Pacific"
        """)
      with self.assertRaises(IOError):
        config_loader.Load(os.path.join(temp_dir, 'config.yaml'))

  def testSyntaxError(self):
    """Loads a file with broken syntax."""
    with _TemporaryDirectory() as temp_dir:
      with open(os.path.join(temp_dir, 'config.yaml'), 'w') as f:
        f.write("""
          test:
            !hoge
        """)
      with self.assertRaises(yaml.YAMLError):
        config_loader.Load(os.path.join(temp_dir, 'config.yaml'))


@contextlib.contextmanager
def _TemporaryDirectory():
  """Creates a temporary directory and cleans it up automatically."""
  temp_dir = tempfile.mkdtemp()
  try:
    yield temp_dir
  finally:
    shutil.rmtree(temp_dir)
