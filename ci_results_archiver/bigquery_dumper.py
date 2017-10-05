# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Dumps BigQuery tables to Google Cloud Storage."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class BigQueryDumper(object):
  """Dumps BigQuery tables to Google Cloud Storage."""

  def __init__(self, bigquery_tables, table_spec, bucket_name):
    """Constructor.

    Args:
      bigquery_tables: BigQueryTables object.
      table_spec: TableSpec object.
      bucket_name: Destination bucket name.
    """
    self._bigquery_tables = bigquery_tables
    self._table_spec = table_spec
    self._bucket_name = bucket_name

  def DumpTables(self, table_suffixes):
    """Dumps BigQuery tables to Google Cloud Storage.

    Args:
      table_suffixes: A list of BigQuery table name suffixes to be dumped.
    """
    if not table_suffixes:
      return
    for table_suffix in sorted(table_suffixes):
      destination_url = 'gs://%s/archives/%s%s.json.gz' % (
          self._bucket_name, self._table_spec.table_prefix, table_suffix)
      self._bigquery_tables.ExportToStorage(table_suffix, destination_url)
