# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for bigquery_exporter."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import unittest

import pytz

from ci_results_archiver import bigquery_exporter
from ci_results_archiver import table_specs
from ci_results_archiver import table_types
from ci_results_archiver.utils.test import fake_bigquery_tables

APR_1 = pytz.utc.localize(datetime.datetime(2017, 4, 1))
APR_2 = pytz.utc.localize(datetime.datetime(2017, 4, 2))
APR_3 = pytz.utc.localize(datetime.datetime(2017, 4, 3))


class BigQueryExporterTestCase(unittest.TestCase):
  """Unit tests for BigQueryExporter."""

  def setUp(self):
    """Common setup for tests."""
    table_spec = table_specs.GetTableSpec(table_types.TableType.AFE_JOBS)
    self.bigquery_tables = fake_bigquery_tables.FakeBigQueryTables(
        table_spec, tables={})
    self.exporter = bigquery_exporter.BigQueryExporter(self.bigquery_tables,
                                                       table_spec)

  def testNew(self):
    """All entries are new."""
    table_suffixes = self.exporter.ExportNewEntries([
        {
            'afe_job_id': 111,
            'created_on': APR_1,
        },
        {
            'afe_job_id': 222,
            'created_on': APR_2,
        },
        {
            'afe_job_id': 333,
            'created_on': APR_3,
        },
    ])

    self.assertEquals(['20170401', '20170402', '20170403'],
                      sorted(table_suffixes))
    self.assertEquals({
        'afe_jobs20170401': [{
            'afe_job_id': 111,
            'created_on': APR_1,
        }],
        'afe_jobs20170402': [{
            'afe_job_id': 222,
            'created_on': APR_2,
        }],
        'afe_jobs20170403': [{
            'afe_job_id': 333,
            'created_on': APR_3,
        }],
    }, self.bigquery_tables.tables)

  def testExisting(self):
    """Some entries already exist."""
    self.bigquery_tables.tables = {
        'afe_jobs20170401': [
            {'afe_job_id': 111, 'created_on': APR_1},
            {'afe_job_id': 200, 'created_on': APR_1},
        ],
    }

    table_suffixes = self.exporter.ExportNewEntries([
        {
            'afe_job_id': 111,
            'created_on': APR_1,
        },
        {
            'afe_job_id': 222,
            'created_on': APR_1,
        },
        {
            'afe_job_id': 333,
            'created_on': APR_1,
        },
    ])

    self.assertEquals(['20170401'], sorted(table_suffixes))
    self.assertEquals({
        'afe_jobs20170401': [
            {
                'afe_job_id': 111,
                'created_on': APR_1,
            },
            {
                'afe_job_id': 200,
                'created_on': APR_1,
            },
            {
                'afe_job_id': 222,
                'created_on': APR_1,
            },
            {
                'afe_job_id': 333,
                'created_on': APR_1,
            },
        ],
    }, self.bigquery_tables.tables)
