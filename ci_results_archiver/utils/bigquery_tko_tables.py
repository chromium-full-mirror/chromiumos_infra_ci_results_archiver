# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""BigQueryTables specialized for TKO tables."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from google.cloud import bigquery  # pylint: disable=import-error,no-name-in-module

from ci_results_archiver import table_types
from ci_results_archiver.utils import bigquery_tables

# Query to get a list of TKO test IDs.
_TKO_TEST_IDS_QUERY = """
SELECT
  t.tko_test_id
FROM
  `%s` AS j,
  j.tests AS t
;
"""

# Query to invalidate TKO tests.
_TKO_TEST_INVALIDATION_QUERY = """
UPDATE `%s`
SET
  tests = ARRAY(
    SELECT AS STRUCT
      *
      REPLACE (
        invalid OR (tko_test_id IN UNNEST(@invalid_tko_test_ids)) AS invalid)
    FROM UNNEST(tests))
WHERE true
;
"""


class BigQueryTkoTables(bigquery_tables.BigQueryTables):
  """BigQueryTables specialized for TKO tables

  This class provides TKO-specific methods in addition to original
  BigQueryTables methods.
  """

  def __init__(self, bigquery_wrapper, table_spec):
    """Constructor.

    Args:
      bigquery_wrapper: BigQueryWrapper object.
      table_spec: TableSpec object. Its type must be TKO_JOBS.
    """
    assert table_spec.table_type == table_types.TableType.TKO_JOBS
    super(BigQueryTkoTables, self).__init__(bigquery_wrapper, table_spec)

  def QueryAllTkoTestIds(self, table_suffix):
    """Queries IDs of all TKO test entries in a table.

    This method is valid only for TKO tables.

    Args:
      table_suffix: Table name suffix.

    Returns:
      A list of TKO test IDs.

    Raises:
      google.cloud.exceptions.GoogleCloudError: On Google Cloud errors.
    """
    table_name = self._table_spec.table_prefix + table_suffix
    rows = self._bigquery_wrapper.RunQuery(
        _TKO_TEST_IDS_QUERY % table_name,
        timeout_seconds=60,
        description=('Getting TKO test IDs in %s' % table_name))
    return [row[0] for row in rows]

  def InvalidateTkoTests(self, table_suffix, invalid_tko_test_ids):
    """Invalidates TKO test entries in a table.

    This method is valid only for TKO tables.

    "Invalidation" means setting `invalid` column to TRUE.

    Args:
      table_suffix: Table name suffix.
      invalid_tko_test_ids: A list of TKO test IDs to be invalidated.

    Raises:
      google.cloud.exceptions.GoogleCloudError: On Google Cloud errors.
    """
    table_name = self._table_spec.table_prefix + table_suffix
    invalid_tko_test_ids_param = bigquery.ArrayQueryParameter(
        'invalid_tko_test_ids', 'INT64', invalid_tko_test_ids)
    self._bigquery_wrapper.RunQuery(
        _TKO_TEST_INVALIDATION_QUERY % table_name,
        params=[invalid_tko_test_ids_param],
        timeout_seconds=300,
        description='Invalidating TKO tests')
