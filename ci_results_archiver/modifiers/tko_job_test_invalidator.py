# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Modifies TKO job tables to invalidate TKO test entries."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

from ci_results_archiver.modifiers import abstract_modifier

# Number of recent tables to run invalidation queries over.
_NUM_RECENT_TABLES = 7


class TkoJobTestInvalidator(abstract_modifier.AbstractModifier):
  """Modifies TKO job tables to invalidate TKO test entries.

  Rows in TKO tko_tests table can be invalidated when a test result
  is overridden by a retry run (see tko/parse.py). In this case,
  `invalid` column of an overridden test is set to true.

  This modifier receives a list of TKO test IDs to invalidate from
  TkoJobImporter and performs modifications to existing BigQuery tables.
  """

  def __init__(self, bigquery_tables):
    """Constructor.

    Args:
      bigquery_tables: BigQueryTkoTables object.
    """
    self._bigquery_tables = bigquery_tables

  def ModifyEntries(self, invalid_tko_test_ids):
    """Invalidates TKO test entries in recent BigQuery tables.

    Implements AbstractModifier.modify_entries().

    Note that this function receives TKO *test* IDs, not TKO job IDs.

    Args:
      invalid_tko_test_ids: A list of TKO test IDs to invalidate.

    Raises:
      google.cloud.exceptions.GoogleCloudError: On Google Cloud errors.
    """
    if not invalid_tko_test_ids:
      return

    logging.info('Invalidating %d tests.', len(invalid_tko_test_ids))

    all_table_suffixes = self._bigquery_tables.ListTableSuffixes()
    all_table_suffixes.reverse()
    recent_table_suffixes = all_table_suffixes[:_NUM_RECENT_TABLES]

    invalidating_id_set = set(invalid_tko_test_ids)

    for table_suffix in recent_table_suffixes:
      table_ids = self._bigquery_tables.QueryAllTkoTestIds(table_suffix)
      hit_id_set = set(table_ids) & invalidating_id_set
      if not hit_id_set:
        logging.info('No test to invalidate in %s.', table_suffix)
      else:
        self._bigquery_tables.InvalidateTkoTests(table_suffix,
                                                 sorted(hit_id_set))
        logging.info('Invalidated %d tests in %s.',
                     len(hit_id_set), table_suffix)
      invalidating_id_set -= hit_id_set
      if not invalidating_id_set:
        break

    if invalidating_id_set:
      logging.warning('Following TKO tests were not found in recent tables: %s',
                      ', '.join(str(i) for i in sorted(invalidating_id_set)))
