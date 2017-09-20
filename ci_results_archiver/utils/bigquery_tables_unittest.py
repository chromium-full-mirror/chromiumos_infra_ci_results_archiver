# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for bigquery_tables."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest

import mock

from ci_results_archiver import table_specs
from ci_results_archiver import table_types
from ci_results_archiver.utils import bigquery_wrapper
from ci_results_archiver.utils import bigquery_tables


class BigQueryTablesTestCase(unittest.TestCase):
  """Unit tests for BigQueryTables."""

  def testListTableSuffixes(self):
    """ListTableSuffixes() works."""
    wrapper = mock.create_autospec(bigquery_wrapper.BigQueryWrapper)
    wrapper.ListTableNames.return_value = [
        'afe_jobs20170401',
        'afe_jobs20170402',
        'tko_jobs20170403',
        'tko_jobs20170404',
    ]

    table_spec = table_specs.GetTableSpec(table_types.TableType.AFE_JOBS)
    tables = bigquery_tables.BigQueryTables(wrapper, table_spec)

    self.assertEquals([
        '20170401',
        '20170402',
    ], tables.ListTableSuffixes())
