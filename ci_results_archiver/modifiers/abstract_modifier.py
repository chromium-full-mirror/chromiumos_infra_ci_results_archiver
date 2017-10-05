# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Interface definition of Modifier."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import abc


class AbstractModifier(object):
  """Interface of Modifier.

  A modifier will modify entries in existing BigQuery tables, given a list
  of entry IDs to modify from an importer.
  """

  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def ModifyEntries(self, modify_ids):
    """Modify entries in existing BigQuery tables.

    Args:
      modify_ids: List of entry IDs to modify, returned from
        Importer.import_entries().

    Returns:
      A list of name suffixes of modified BigQuery tables.

    Raises:
      google.cloud.exceptions.GoogleCloudError: On Google Cloud errors.
    """
    raise NotImplementedError()
