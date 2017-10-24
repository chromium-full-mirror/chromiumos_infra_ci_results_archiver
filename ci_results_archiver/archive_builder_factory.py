# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Provides a factory function of ArchiveBuilder."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from chromite.lib import cidb as cidb_lib
from google.cloud import bigquery  # pylint: disable=import-error,no-name-in-module
from google.cloud import storage  # pylint: disable=import-error,no-name-in-module
import pytz

from ci_results_archiver import archive_builder
from ci_results_archiver import bigquery_dumper
from ci_results_archiver import bigquery_exporter
from ci_results_archiver import checkpointer as checkpointer_lib
from ci_results_archiver import table_specs
from ci_results_archiver import table_types
from ci_results_archiver.importers import afe_job_importer
from ci_results_archiver.importers import cidb_build_importer
from ci_results_archiver.importers import grace_period as grace_period_lib
from ci_results_archiver.importers import tko_job_importer
from ci_results_archiver.modifiers import tko_job_test_invalidator
from ci_results_archiver.utils import afe_connection
from ci_results_archiver.utils import bigquery_tables as bigquery_tables_lib
from ci_results_archiver.utils import bigquery_tko_tables
from ci_results_archiver.utils import bigquery_wrapper as bigquery_wrapper_lib
from ci_results_archiver.utils import mysql_wrapper
from ci_results_archiver.utils import text_util
from ci_results_archiver.utils import tko_connection


def CreateBuilder(table_type, configs):
  """Creates an ArchiveBuilder object.

  Args:
    table_type: TableType value of the desired archive table.
    configs: Configuration dictionary.

  Returns:
    ArchiveBuilder object.

  Raises:
    ValueError: When |table_type| is not a valid archive table type.
  """
  # This will raise ValueError if |table_type| is not a valid archive table
  # type.
  table_spec = table_specs.GetTableSpec(table_type)

  bigquery_client = bigquery.Client(configs['bigquery']['project'])
  dataset = bigquery_client.dataset(configs['bigquery']['dataset'])
  storage_client = storage.Client(configs['cloud_storage']['project'])
  temporary_bucket = storage_client.bucket(
      configs['cloud_storage']['temporary_bucket'])
  persistent_bucket = storage_client.bucket(
      configs['cloud_storage']['persistent_bucket'])

  bigquery_wrapper = bigquery_wrapper_lib.BigQueryWrapper(
      bigquery_client=bigquery_client,
      dataset=dataset,
      storage_client=storage_client,
      bucket=temporary_bucket)

  if table_type == table_types.TableType.TKO_JOBS:
    bigquery_tables = bigquery_tko_tables.BigQueryTkoTables(
        bigquery_wrapper=bigquery_wrapper, table_spec=table_spec)
  else:
    bigquery_tables = bigquery_tables_lib.BigQueryTables(
        bigquery_wrapper=bigquery_wrapper, table_spec=table_spec)

  importer = _CreateImporter(
      table_type=table_type, table_spec=table_spec, configs=configs)

  modifier = _CreateModifier(
      table_type=table_type, bigquery_tables=bigquery_tables)

  exporter = bigquery_exporter.BigQueryExporter(
      bigquery_tables=bigquery_tables, table_spec=table_spec)

  dump_enabled = configs['tables'][table_type.value].get('dump', True)
  if dump_enabled:
    dumper = bigquery_dumper.BigQueryDumper(
        bigquery_tables=bigquery_tables,
        table_spec=table_spec,
        bucket_name=persistent_bucket.name)
  else:
    dumper = None

  checkpointer = checkpointer_lib.Checkpointer(
      bucket=persistent_bucket,
      dataset=dataset.name,
      table_prefix=table_spec.table_prefix)

  return archive_builder.ArchiveBuilder(
      table_type=table_type,
      importer=importer,
      modifier=modifier,
      exporter=exporter,
      dumper=dumper,
      checkpointer=checkpointer)


def _CreateImporter(table_type, table_spec, configs):
  """Creates an Importer object.

  Args:
    table_type: TableType value of the desired archive table.
    table_spec: TableSpec object.
    configs: Configuration dictionary.

  Returns:
    AbstractImporter object.

  Raises:
    KeyError: On unsupported table_type.
  """
  table_configs = configs['tables'][table_type.value]
  max_entries = table_configs['max_entries']
  grace_period_configs = table_configs['grace_period']
  grace_period = _CreateGracePeriod(
      table_spec=table_spec, grace_period_configs=grace_period_configs)

  if table_type == table_types.TableType.TKO_JOBS:
    tko = tko_connection.TkoConnection(_CreateMySQLWrapper('tko', configs))
    return tko_job_importer.TkoJobImporter(
        tko=tko, max_entries=max_entries, grace_period=grace_period)
  if table_type == table_types.TableType.AFE_JOBS:
    afe = afe_connection.AfeConnection(_CreateMySQLWrapper('afe', configs))
    return afe_job_importer.AfeJobImporter(
        afe=afe, max_entries=max_entries, grace_period=grace_period)
  if table_type == table_types.TableType.CIDB_BUILDS:
    cidb = _CreateCIDBConnection(configs)
    return cidb_build_importer.CidbBuildImporter(
        cidb=cidb, max_entries=max_entries, grace_period=grace_period)
  assert False, 'Unexpected table_type: %r' % table_type


def _CreateModifier(table_type, bigquery_tables):
  """Creates a Modifier object.

  Args:
    table_type: TableType value of the desired archive table.
    bigquery_tables: BigQueryTables object.

  Returns:
    AbstractModifier object, or None.
  """
  if table_type == table_types.TableType.TKO_JOBS:
    return tko_job_test_invalidator.TkoJobTestInvalidator(
        bigquery_tables=bigquery_tables)
  if table_type in (table_types.TableType.AFE_JOBS,
                    table_types.TableType.CIDB_BUILDS):
    return None
  assert False, 'Unexpected table_type: %r' % table_type


def _CreateMySQLWrapper(database_name, configs):
  """Instantiates MySQLWrapper object with credentials in config files.

  Args:
    database_name: Database name.
    configs: Configuration dictionary.

  Returns:
    MySQLWrapper object.
  """
  database = configs['databases'][database_name]
  creds = database['credentials']
  return mysql_wrapper.MySQLWrapper(
      hostname=creds['hostname'],
      username=creds['username'],
      password=creds['password'],
      database=creds['database'],
      timezone=pytz.timezone(database['timezone']))


def _CreateCIDBConnection(configs):
  """Instantiates CIDBConnection object with credentials in config files.

  Args:
    configs: Configuration dictionary.

  Returns:
    CIDBConnection object.
  """
  return cidb_lib.CIDBConnection(configs['cidb']['credentials_dir'])


def _CreateGracePeriod(table_spec, grace_period_configs):
  """Creates a GracePeriod object from a config dictionary.

  Args:
    table_spec: TableSpec object.
    grace_period_configs: A config dictionary.

  Returns:
    GracePeriod object.
  """
  timeout_str = grace_period_configs.get('timeout')
  timeout = text_util.ParseTimeDelta(timeout_str) if timeout_str else None
  capacity = grace_period_configs.get('capacity')
  return grace_period_lib.GracePeriod(
      id_column=table_spec.id_column,
      insertion_timestamp_column=table_spec.insertion_timestamp_column,
      timeout=timeout,
      capacity=capacity)
