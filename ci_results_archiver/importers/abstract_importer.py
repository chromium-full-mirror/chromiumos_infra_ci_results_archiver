# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Interface definition of Importer."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import abc


class AbstractImporter(object):
  """Interface of Importer.

  An importer is the "source" part of BigQuery archive table builder. It
  will read entries from databases and return as a list of dictionaries.
  """

  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def ImportEntries(self, next_id):
    """Imports entries from databases.

    Args:
      next_id: An integer representing the ID of an entry. Importer
        implementation must process entries whose ID is no less than this
        ID.

    Returns:
      (entries, modify_ids, new_next_id) where:
        entries: A list of dictionaries representing entries.
        modify_ids: List of entry IDs to modify which will be later passed
            to Modifier.modify_entries().
        new_next_id: New next_id.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    raise NotImplementedError()
