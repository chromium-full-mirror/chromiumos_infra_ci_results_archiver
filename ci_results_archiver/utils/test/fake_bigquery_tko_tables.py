# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Fake implementation of BigQueryTkoTables."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from ci_results_archiver import table_types
from ci_results_archiver.utils.test import fake_bigquery_tables


class FakeBigQueryTkoTables(fake_bigquery_tables.FakeBigQueryTables):
  """Fake implementation of BigQueryTkoTables."""

  def __init__(self, table_spec, tables):
    """Constructor."""
    assert table_spec.table_type == table_types.TableType.TKO_JOBS
    super(FakeBigQueryTkoTables, self).__init__(table_spec, tables)

  def QueryAllTkoTestIds(self, table_suffix):
    """Queries IDs of all TKO test entries in a table."""
    test_ids = []
    table_name = self._table_spec.table_prefix + table_suffix
    entries = self.tables.get(table_name, [])
    for entry in entries:
      for test in entry['tests']:
        test_ids.append(test['tko_test_id'])
    return test_ids

  def InvalidateTkoTests(self, table_suffix, invalid_tko_test_ids):
    """Invalidates TKO test entries in a table."""
    assert self._table_spec.table_type == table_types.TableType.TKO_JOBS
    table_name = self._table_spec.table_prefix + table_suffix
    entries = self.tables.get(table_name, [])
    for entry in entries:
      for test in entry['tests']:
        if test['tko_test_id'] in invalid_tko_test_ids:
          test['invalid'] = True
