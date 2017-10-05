# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for bigquery_dumper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest

from ci_results_archiver import bigquery_dumper
from ci_results_archiver import table_specs
from ci_results_archiver import table_types
from ci_results_archiver.utils.test import fake_bigquery_tables


class BigQueryDumperTestCase(unittest.TestCase):
  """Unit tests for BigQueryDumper."""

  def setUp(self):
    """Common setup for tests."""
    self.table_spec = table_specs.GetTableSpec(table_types.TableType.AFE_JOBS)
    self.bigquery_tables = fake_bigquery_tables.FakeBigQueryTables(
        self.table_spec, tables={})

  def testNormal(self):
    """Works normally."""
    dumper = bigquery_dumper.BigQueryDumper(self.bigquery_tables,
                                            self.table_spec, 'somebucket')
    dumper.DumpTables(['20170401', '20170403'])

    self.assertEquals({
        'gs://somebucket/archives/afe_jobs20170401.json.gz': 'afe_jobs20170401',
        'gs://somebucket/archives/afe_jobs20170403.json.gz': 'afe_jobs20170403',
    }, self.bigquery_tables.exports)

  def testEmpty(self):
    """Works when the table suffix list is empty."""
    dumper = bigquery_dumper.BigQueryDumper(self.bigquery_tables,
                                            self.table_spec, 'somebucket')
    dumper.DumpTables([])

    self.assertEquals({}, self.bigquery_tables.exports)
