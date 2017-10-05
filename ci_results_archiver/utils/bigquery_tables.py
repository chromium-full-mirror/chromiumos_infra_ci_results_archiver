# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Helper to manipulate BigQuery tables."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class BigQueryTables(object):
  """Helper to manipulate BigQuery tables.

  This object manages a collection of BigQuery tables sharing the same name
  prefix. Individual table can be specified by a name suffix.
  """

  def __init__(self, bigquery_wrapper, table_spec):
    """Constructor.

    Args:
      bigquery_wrapper: BigQueryWrapper object.
      table_spec: TableSpec object.
    """
    self._bigquery_wrapper = bigquery_wrapper
    self._table_spec = table_spec

  def ListTableSuffixes(self):
    """Retrieves a list of table name suffixes.

    Returns:
      A sorted list of table name suffixes.

    Raises:
      google.cloud.exceptions.GoogleCloudError: On Google Cloud errors.
    """
    table_prefix = self._table_spec.table_prefix
    prefix_len = len(table_prefix)
    table_suffixes = [
        table_name[prefix_len:]
        for table_name in self._bigquery_wrapper.ListTableNames()
        if table_name.startswith(table_prefix)
    ]
    return table_suffixes

  def QueryAllIds(self, table_suffix):
    """Queries IDs of all entries in a table.

    Args:
      table_suffix: Table name suffix.

    Returns:
      A list of IDs.
    """
    table_name = self._table_spec.table_prefix + table_suffix
    if not self._bigquery_wrapper.TableExists(table_name):
      return []
    rows = self._bigquery_wrapper.RunQuery(
        'SELECT `%s` AS id FROM `%s`' % (self._table_spec.id_column,
                                         table_name),
        timeout_seconds=60,
        description=('Getting ID list in %s' % table_name))
    return [row[0] for row in rows]

  def LoadEntries(self, table_suffix, schema, entries):
    """Loads entries into a table.

    Entries are first serialized as newline-delimited JSON and uploaded to
    Google Cloud Storage, then a load job is requested to BigQuery.

    The target table is created if it does not exist yet. Entries are always
    appended to the table and do not overwrite existing entries.

    Args:
      table_suffix: Table name suffix.
      schema: Schema of the table as a list of SchemaField.
      entries: A list of dictionaries representing entries.

    Raises:
      google.cloud.exceptions.GoogleCloudError: On Google Cloud errors.
    """
    table_name = self._table_spec.table_prefix + table_suffix
    self._bigquery_wrapper.LoadEntries(table_name, schema, entries)

  def ExportToStorage(self, table_suffix, destination_url):
    """Exports a table into Google Cloud Storage.

    A table is exported as a gzip'ed newline-delimited JSON file.

    Args:
      table_suffix: Table name suffix.
      destination_url: Destination URL starting with gs://.

    Raises:
      google.cloud.exceptions.GoogleCloudError: On Google Cloud errors.
    """
    table_name = self._table_spec.table_prefix + table_suffix
    self._bigquery_wrapper.ExportToStorage(table_name, destination_url)
