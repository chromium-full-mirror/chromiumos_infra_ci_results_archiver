# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""BigQuery table specifications.

This schema definition is part of chromeos-infra's API to downstream result
consumers.

The usual rules of API data definitions apply here. To make our life easy:
 - No field should be required.
 - No field should ever be removed.
 - No field should have its type (BigQuery type) changed.

If you want to make a breaking change to the semantics of a field, you MUST
deprecate the existing field, add a new field with the new semantics, and
provide downstream users warning and lead-out time before you stop populating
the deprecated field. You must almost never drop the old field (but you can
eventually stop populating it).
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections

from google.cloud import bigquery  # pylint: disable=import-error,no-name-in-module

from ci_results_archiver import table_types

TableSpec = collections.namedtuple(
    'TableSpec',
    [
        # Table type.
        'table_type',
        # BigQuery table prefix.
        'table_prefix',
        # Primary ID column.
        'id_column',
        # Timestamp column to use on partitioning BigQuery tables.
        'partition_timestamp_column',
        # Timestamp column of insertion time.
        'insertion_timestamp_column',
        # BigQuery table schema.
        'schema',
    ])

AFE_JOBS = TableSpec(
    table_type=table_types.TableType.AFE_JOBS,
    table_prefix='afe_jobs',
    id_column='afe_job_id',
    # afe_jobs.created_on matches with tko_tests.queued_time.
    partition_timestamp_column='created_on',
    insertion_timestamp_column='created_on',
    schema=[
        bigquery.SchemaField('afe_job_id', 'INTEGER', 'NULLABLE'),
        bigquery.SchemaField('afe_parent_job_id', 'INTEGER', 'NULLABLE'),
        bigquery.SchemaField('owner', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('name', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('priority', 'INTEGER', 'NULLABLE'),
        bigquery.SchemaField('control_file', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('control_type', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('created_on', 'TIMESTAMP', 'NULLABLE'),
        bigquery.SchemaField('synch_count', 'INTEGER', 'NULLABLE'),
        bigquery.SchemaField('run_verify', 'BOOLEAN', 'NULLABLE'),
        bigquery.SchemaField('run_reset', 'BOOLEAN', 'NULLABLE'),
        bigquery.SchemaField('timeout_mins', 'INTEGER', 'NULLABLE'),
        bigquery.SchemaField('max_runtime_mins', 'INTEGER', 'NULLABLE'),
        bigquery.SchemaField('reboot_before', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('reboot_after', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('parse_failed_repair', 'BOOLEAN', 'NULLABLE'),
        bigquery.SchemaField('test_retry', 'INTEGER', 'NULLABLE'),
        bigquery.SchemaField('shard', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('require_ssp', 'BOOLEAN', 'NULLABLE'),
        bigquery.SchemaField(
            'keyvals',
            'RECORD',
            'REPEATED',
            fields=[
                bigquery.SchemaField('key', 'STRING', 'NULLABLE'),
                bigquery.SchemaField('value', 'STRING', 'NULLABLE'),
            ]),
        bigquery.SchemaField('dependency_labels', 'STRING', 'REPEATED'),
    ])

TKO_JOBS = TableSpec(
    table_type=table_types.TableType.TKO_JOBS,
    table_prefix='tko_jobs',
    id_column='tko_job_id',
    # queued_time matches with afe_jobs.created_on.
    partition_timestamp_column='partition_timestamp',
    # tko_jobs table does not have an insertion timestamp column.
    insertion_timestamp_column=None,
    schema=[
        bigquery.SchemaField('tko_job_id', 'INTEGER', 'NULLABLE'),
        # Deprecated. Use task_id instead.
        bigquery.SchemaField('afe_job_id', 'INTEGER', 'NULLABLE'),
        # Deprecated. Use parent_task_id instead.
        bigquery.SchemaField('afe_parent_job_id', 'INTEGER', 'NULLABLE'),
        bigquery.SchemaField('task_reference_type', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('task_id', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('parent_task_id', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('username', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('suite', 'STRING', 'NULLABLE'),
        # Equals queued_time for AFE jobs and started_time for Skylab tasks
        bigquery.SchemaField('partition_timestamp', 'TIMESTAMP', 'NULLABLE'),
        bigquery.SchemaField('queued_time', 'TIMESTAMP', 'NULLABLE'),
        bigquery.SchemaField('started_time', 'TIMESTAMP', 'NULLABLE'),
        bigquery.SchemaField('finished_time', 'TIMESTAMP', 'NULLABLE'),
        bigquery.SchemaField('build', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('build_version', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('board', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('hostname', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('label', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('tag', 'STRING', 'NULLABLE'),
        bigquery.SchemaField(
            'tests',
            'RECORD',
            'REPEATED',
            fields=[
                bigquery.SchemaField('tko_test_id', 'INTEGER', 'NULLABLE'),
                bigquery.SchemaField('test', 'STRING', 'NULLABLE'),
                bigquery.SchemaField('status', 'STRING', 'NULLABLE'),
                bigquery.SchemaField('started_time', 'TIMESTAMP', 'NULLABLE'),
                bigquery.SchemaField('finished_time', 'TIMESTAMP', 'NULLABLE'),
                bigquery.SchemaField('reason', 'STRING', 'NULLABLE'),
                bigquery.SchemaField('hostname', 'STRING', 'NULLABLE'),
                bigquery.SchemaField('subdir', 'STRING', 'NULLABLE'),
                bigquery.SchemaField('invalid', 'BOOLEAN', 'NULLABLE'),
                bigquery.SchemaField('invalidating_tko_test_id', 'INTEGER',
                                     'NULLABLE'),
            ]),
        bigquery.SchemaField(
            'keyvals',
            'RECORD',
            'REPEATED',
            fields=[
                bigquery.SchemaField('key', 'STRING', 'NULLABLE'),
                bigquery.SchemaField('value', 'STRING', 'NULLABLE'),
            ]),
    ])

CIDB_BUILDS = TableSpec(
    table_type=table_types.TableType.CIDB_BUILDS,
    table_prefix='cidb_builds',
    id_column='cidb_build_id',
    partition_timestamp_column='start_time',
    insertion_timestamp_column='start_time',
    schema=[
        bigquery.SchemaField('cidb_build_id', 'INTEGER', 'NULLABLE'),
        bigquery.SchemaField('cidb_master_build_id', 'INTEGER', 'NULLABLE'),
        bigquery.SchemaField('builder_name', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('buildbot_generation', 'INTEGER', 'NULLABLE'),
        bigquery.SchemaField('waterfall', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('build_number', 'INTEGER', 'NULLABLE'),
        bigquery.SchemaField('build_config', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('bot_hostname', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('start_time', 'TIMESTAMP', 'NULLABLE'),
        bigquery.SchemaField('important', 'BOOLEAN', 'NULLABLE'),
        bigquery.SchemaField('buildbucket_id', 'STRING', 'NULLABLE'),
        bigquery.SchemaField('deadline', 'TIMESTAMP', 'NULLABLE'),
        bigquery.SchemaField('branch', 'STRING', 'NULLABLE'),
    ])

_ALL_SPECS = (AFE_JOBS, TKO_JOBS, CIDB_BUILDS)


def GetTableSpec(table_type):
  """Returns a TableSpec object corresponding to the specified table type.

  Args:
    table_type: TableType enum value.

  Returns:
    TableSpec object.

  Raises:
    ValueError: If the specified table type is not known.
  """
  for spec in _ALL_SPECS:
    if spec.table_type == table_type:
      return spec
  raise ValueError('Unexpected table_type: %r' % table_type)
