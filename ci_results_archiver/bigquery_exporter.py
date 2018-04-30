# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Exports new entries into BigQuery tables."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import logging


class BigQueryExporter(object):
  """Exports new entries into BigQuery tables.

  An exporter is the "sink" part of BigQuery archive table builder. It
  will write entries to BigQuery tables.
  """

  def __init__(self, bigquery_tables, table_spec):
    """Constructor.

    Args:
      bigquery_tables: BigQueryTables object.
      table_spec: TableSpec object.
    """
    self._bigquery_tables = bigquery_tables
    self._table_spec = table_spec

  def ExportNewEntries(self, entries):
    """Exports new entries to BigQuery tables.

    This function is designed to be idempotent. In case there are already
    existing entries with the same IDs, they are preserved and we never
    insert conflicting entries.

    Args:
      entries: A list of dictionaries representing entries.

    Returns:
      (exported_table_suffixes, unexported_entries) where:
          exported_table_suffixes: A list of name suffixes of updated BigQuery
              tables.
          unexported_entries: Entries that could not be exported to bigquery.
    """
    if not entries:
      return [], []
    entries_by_date, unpartitioned_entries = _PartitionByDate(
        entries, self._table_spec.partition_timestamp_column)
    exported_table_suffixes = []
    for date, entries_in_date in sorted(entries_by_date.items()):
      table_suffix = date.strftime('%Y%m%d')
      self._ExportNewEntriesToTable(table_suffix, entries_in_date)
      exported_table_suffixes.append(table_suffix)
    return exported_table_suffixes, unpartitioned_entries

  def _ExportNewEntriesToTable(self, table_suffix, entries):
    """Exports new entries to a specified BigQuery table.

    Args:
      table_suffix: Table name suffix.
      entries: A list of dictionaries representing entries.
    """
    existing_id_set = set(self._bigquery_tables.QueryAllIds(table_suffix))
    new_entries = [
        e for e in entries
        if e[self._table_spec.id_column] not in existing_id_set
    ]
    if len(new_entries) != len(entries):
      logging.warning('Skipping %d already existing entries.',
                      len(entries) - len(new_entries))
    if new_entries:
      self._bigquery_tables.LoadEntries(table_suffix, self._table_spec.schema,
                                        new_entries)


def _PartitionByDate(entries, timestamp_column):
  """Partitions entries by date.

  Args:
    entries: A list of dictionaries representing entries.
    timestamp_column: Name of timestamp column to be used on partitioning
      entries.

  Returns:
    ({date: entries_in_date}, unpartitioned_entries) where:
      date: datetime.date object.
      entries_in_date: A list of dictionaries representing entries in the
          corresponding date.
      unpartitioned_entries: A list of entries that could not be partitioned
          into any table. This can happen if the column used to partition the
          entries is unset.
  """
  entries_by_date = collections.defaultdict(list)
  unpartitioned_entries = []
  for entry in entries:
    entry_timestamp = entry.get(timestamp_column)
    if not entry_timestamp:
      unpartitioned_entries.append(entry)
      continue
    date = entry_timestamp.date()
    entries_by_date[date].append(entry)
  return dict(entries_by_date), unpartitioned_entries
