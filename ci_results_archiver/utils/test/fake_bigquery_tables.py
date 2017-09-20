# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Fake implementation of BigQueryTables."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class FakeBigQueryTables(object):
  """Fake implementation of BigQueryTables.

  Attributes:
    tables: Map from a table name to a list of entries.
  """

  def __init__(self, table_spec, tables):
    """Constructor.

    Args:
      table_spec: TableSpec object.
      tables: Map from a table name to a list of entries.
    """
    self._table_spec = table_spec
    self.tables = tables

  def ListTableSuffixes(self):
    """Retrieves a list of table name suffixes."""
    table_prefix = self._table_spec.table_prefix
    prefix_len = len(table_prefix)
    table_suffixes = [
        table_name[prefix_len:] for table_name in sorted(self.tables)
        if table_name.startswith(table_prefix)
    ]
    return table_suffixes

  def QueryAllIds(self, table_suffix):
    """Queries IDs of all entries in a table."""
    table_name = self._table_spec.table_prefix + table_suffix
    entries = self.tables.get(table_name, [])
    return [entry[self._table_spec.id_column] for entry in entries]

  def LoadEntries(self, table_suffix, schema, entries):
    """Loads entries into a table."""
    del schema  # unused
    table_name = self._table_spec.table_prefix + table_suffix
    for entry in entries:
      self.tables.setdefault(table_name, []).append(entry)
