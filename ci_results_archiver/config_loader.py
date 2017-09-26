# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Configuration file parser.

Configurations are written in YAML files. In addition to standard YAML syntax,
we support a custom tag "!import" to include another YAML file recursively.
This is useful to keep usual configs and credentials separated.

For example:

  databases:
    tko:
      credentials: !import "/path/to/creds.yaml"
      timezone: "US/Pacific"
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

import yaml


def Load(config_path):
  """Loads configs from YAML file and returns as a dictionary.

  Args:
    config_path: Path to a config file.

  Returns:
    Dictionary.

  Raises:
    IOError: On I/O errors (e.g. file does not exist).
    yaml.YAMLError: On YAML load errors (e.g. syntax errors).
  """

  class CustomLoader(yaml.Loader):
    """Custom loader accepting !import custom tag."""

  def ConstructImport(loader, node):
    """Processes !import tag."""
    new_config_path = os.path.join(
        os.path.dirname(config_path), loader.construct_scalar(node))
    return Load(new_config_path)

  CustomLoader.add_constructor('!import', ConstructImport)

  with open(config_path) as f:
    return yaml.load(f, CustomLoader)
