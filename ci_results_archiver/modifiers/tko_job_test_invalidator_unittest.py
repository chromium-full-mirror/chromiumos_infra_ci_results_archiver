# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for tko_job_test_invalidator."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest

from ci_results_archiver import table_specs
from ci_results_archiver import table_types
from ci_results_archiver.modifiers import tko_job_test_invalidator
from ci_results_archiver.utils.test import fake_bigquery_tko_tables


class TkoJobTestInvalidatorTestCase(unittest.TestCase):
  """Unit tests for TkoJobTestInvalidator."""

  def setUp(self):
    """Setup."""
    tables = {
        'tko_jobs20170401': [
            {
                'tko_job_id': 110,
                'tests': [
                    {'tko_test_id': 111, 'invalid': False},
                    {'tko_test_id': 112, 'invalid': False},
                ],
            },
            {
                'tko_job_id': 120,
                'tests': [
                    {'tko_test_id': 121, 'invalid': False},
                    {'tko_test_id': 122, 'invalid': False},
                ],
            },
        ],
        'tko_jobs20170402': [
            {
                'tko_job_id': 210,
                'tests': [
                    {'tko_test_id': 211, 'invalid': False},
                    {'tko_test_id': 212, 'invalid': True},
                ],
            },
        ],
    }
    self.bigquery_tables = fake_bigquery_tko_tables.FakeBigQueryTkoTables(
        table_spec=table_specs.GetTableSpec(table_types.TableType.TKO_JOBS),
        tables=tables)
    self.modifier = tko_job_test_invalidator.TkoJobTestInvalidator(
        self.bigquery_tables)

  def testNone(self):
    """Invalidates no entry."""
    self.modifier.ModifyEntries([])

    self.assertEquals({
        'tko_jobs20170401': [
            {
                'tko_job_id': 110,
                'tests': [
                    {'tko_test_id': 111, 'invalid': False},
                    {'tko_test_id': 112, 'invalid': False},
                ],
            },
            {
                'tko_job_id': 120,
                'tests': [
                    {'tko_test_id': 121, 'invalid': False},
                    {'tko_test_id': 122, 'invalid': False},
                ],
            },
        ],
        'tko_jobs20170402': [
            {
                'tko_job_id': 210,
                'tests': [
                    {'tko_test_id': 211, 'invalid': False},
                    {'tko_test_id': 212, 'invalid': True},
                ],
            },
        ],
    }, self.bigquery_tables.tables)

  def testSingle(self):
    """Invalidates a single entry in a single table."""
    self.modifier.ModifyEntries([121])

    self.assertEquals({
        'tko_jobs20170401': [
            {
                'tko_job_id': 110,
                'tests': [
                    {'tko_test_id': 111, 'invalid': False},
                    {'tko_test_id': 112, 'invalid': False},
                ],
            },
            {
                'tko_job_id': 120,
                'tests': [
                    {'tko_test_id': 121, 'invalid': True},
                    {'tko_test_id': 122, 'invalid': False},
                ],
            },
        ],
        'tko_jobs20170402': [
            {
                'tko_job_id': 210,
                'tests': [
                    {'tko_test_id': 211, 'invalid': False},
                    {'tko_test_id': 212, 'invalid': True},
                ],
            },
        ],
    }, self.bigquery_tables.tables)

  def testAlreadyInvalidated(self):
    """Invalidates an already-invalidated entry."""
    self.modifier.ModifyEntries([212])

    self.assertEquals({
        'tko_jobs20170401': [
            {
                'tko_job_id': 110,
                'tests': [
                    {'tko_test_id': 111, 'invalid': False},
                    {'tko_test_id': 112, 'invalid': False},
                ],
            },
            {
                'tko_job_id': 120,
                'tests': [
                    {'tko_test_id': 121, 'invalid': False},
                    {'tko_test_id': 122, 'invalid': False},
                ],
            },
        ],
        'tko_jobs20170402': [
            {
                'tko_job_id': 210,
                'tests': [
                    {'tko_test_id': 211, 'invalid': False},
                    {'tko_test_id': 212, 'invalid': True},
                ],
            },
        ],
    }, self.bigquery_tables.tables)

  def testMissing(self):
    """Invalidates a missing entry."""
    self.modifier.ModifyEntries([999])

    self.assertEquals({
        'tko_jobs20170401': [
            {
                'tko_job_id': 110,
                'tests': [
                    {'tko_test_id': 111, 'invalid': False},
                    {'tko_test_id': 112, 'invalid': False},
                ],
            },
            {
                'tko_job_id': 120,
                'tests': [
                    {'tko_test_id': 121, 'invalid': False},
                    {'tko_test_id': 122, 'invalid': False},
                ],
            },
        ],
        'tko_jobs20170402': [
            {
                'tko_job_id': 210,
                'tests': [
                    {'tko_test_id': 211, 'invalid': False},
                    {'tko_test_id': 212, 'invalid': True},
                ],
            },
        ],
    }, self.bigquery_tables.tables)

  def testMultiple(self):
    """Invalidates multiple entries in multiple tables."""
    self.modifier.ModifyEntries([111, 121, 212])

    self.assertEquals({
        'tko_jobs20170401': [
            {
                'tko_job_id': 110,
                'tests': [
                    {'tko_test_id': 111, 'invalid': True},
                    {'tko_test_id': 112, 'invalid': False},
                ],
            },
            {
                'tko_job_id': 120,
                'tests': [
                    {'tko_test_id': 121, 'invalid': True},
                    {'tko_test_id': 122, 'invalid': False},
                ],
            },
        ],
        'tko_jobs20170402': [
            {
                'tko_job_id': 210,
                'tests': [
                    {'tko_test_id': 211, 'invalid': False},
                    {'tko_test_id': 212, 'invalid': True},
                ],
            },
        ],
    }, self.bigquery_tables.tables)
