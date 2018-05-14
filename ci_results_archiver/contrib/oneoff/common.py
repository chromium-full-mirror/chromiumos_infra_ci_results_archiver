# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Helper methods for one-off data backfilling or update tasks."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import contextlib
import logging
import sys
import time

from google.cloud import bigquery  # pylint: disable=import-error,no-name-in-module

from ci_results_archiver.utils import bigquery_wrapper

_CONCURENT_RUN_CONFIRMATION_MSG = """
One off table update tasks are in general not safe to be run concurrently with
ci_results_archiver, or with each other because they copy / modify tables and
this may interfere with other updates.
Please temporarily disable ci_results_archiver when running these tasks."""


class OneoffError(Exception):
  """Generic error raised from this module."""


class TableUnchanged(Exception):
  """Exception used to indicate that a table update was a no-op."""


def DisplayWarningAndConfirm(options):
  """Spew some common warnings about oneoff tasks."""
  logging.warning(_CONCURENT_RUN_CONFIRMATION_MSG)
  if options.confirm_run:
    logging.info('Accepting confirmation provided in command line.')
  else:
    _ConfirmOrRaise()


def ParserAddOneoffArgs(parser):
  """Add common arguments required for one-off tasks.

  Args:
    parser: An argparse.ArgumentParser object.
  """
  subparser = parser.add_argument_group(
      'bigquery update',
      description='Common arguments for updating bigquery tables')
  subparser.add_argument(
      '--project',
      required=True,
      help='GCP project containing the BigQuery tables.')
  subparser.add_argument(
      '--dataset', required=True, help='BigQuery dataset to target.')
  subparser.add_argument(
      '--table',
      action='append',
      help='Table names to affect.'
      ' May be repeated to specify multiple tables to affect.')
  subparser.add_argument(
      '--gs-dump-bucket',
      help='(Optional) GS path containing dumped tables to be updated.')
  subparser.add_argument(
      '--confirm-run',
      default=False,
      action='store_true',
      help='Confirm that you are aware of concurrent run issues.'
      ' Instructs the task to not prompt for stding confirmation.')


class TableUpdater(object):
  """A class to run a oneoff update on BigQuery tables."""

  def __init__(self, options):
    """Initialize us.

    Args:
      options: Parsed arguments for a parser created using
      ParserAddOneoffArgs().
    """
    self._project = options.project
    self._dataset = options.dataset
    self._table_names = options.table
    self._gs_dump_bucket = options.gs_dump_bucket
    self._tmp_table_name_prefix = 'tmp%d' % time.time()

    bq_client = bigquery.Client(self._project)
    bq_dataset = bq_client.dataset(self._dataset)
    self._bq_wrapper = bigquery_wrapper.BigQueryWrapper(bq_client, bq_dataset)

  def Execute(self, update_table):
    """Execute the oneoff table update for all requested tables.

    Args:
      update_table: The function to execute on each table. This function must
          have the signature:
              update_table(bq_wrapper, table_name)
          where:
              bq_wrapper: A bigquery_wrapper.BigQueryWrapper object.
              table_name: Name of the table to upate.
          If update_table() succeeds  the update will be committed, else all
          changes made by the call will be discarded.
          update_table() may raise TableUnchanged exception to indicate that no
          change was made to the table.
    """
    table_names = self._table_names
    for table_name in table_names:
      if not self._bq_wrapper.TableExists(table_name):
        table_names = self._bq_wrapper.ListTableNames()
        logging.error('Failed to find table. Perhaps you want %s...',
                      table_name[:5])
        raise OneoffError('No table %s.%s in project %s' %
                          (self._dataset, table_name, self._project))

      try:
        with self._ShadowTable(table_name) as tmp_table:
          update_table(self._bq_wrapper, tmp_table)
          logging.info('Successfully updated table %s.%s', self._dataset,
                       table_name)
      except TableUnchanged:
        logging.info('No change in table %s.%s', self._dataset, table_name)
        continue
      if self._gs_dump_bucket:
        self._DumpTable(table_name)

  @contextlib.contextmanager
  def _ShadowTable(self, table_name):
    """Shadow a given table in a temporary table.

    - Copy the given table in a temporary.
    - Yield the temporary table.
    - On success, copy the (updated) temporary back onto original table.
    - Delete the temporary table unless we fail to copy back.

    Args:
      table_name: The table to shadow.
    """
    tmp_table_name = '%s_%s' % (self._tmp_table_name_prefix, table_name)
    self._bq_wrapper.CopyTable(tmp_table_name, table_name)
    try:
      yield tmp_table_name
      self._bq_wrapper.DeleteTable(table_name)
      self._bq_wrapper.CopyTable(table_name, tmp_table_name)
    finally:
      self._bq_wrapper.DeleteTable(tmp_table_name)

  def _DumpTable(self, table_name):
    """Dump a bigquery table to GS.

    Old dump will be backed up in the GS subdirectory provided. You must delete
    backups manually.

    Args:
      table_name: The table to shwadow.
      backup_dir: Name of a subdirectory to use for backing up old table.
    """
    url = 'gs://%s/archives/%s.json.gz' % (self._gs_dump_bucket, table_name)
    self._bq_wrapper.ExportToStorage(table_name, url)
    logging.info('Successfully dumped table %s.%s', self._dataset, table_name)


def _ConfirmOrRaise():
  """Get a confirmation from user on stdin, or raise."""
  logging.warning('Continue? [y/n]')
  confirmation = sys.stdin.readline().strip()
  if confirmation.lower() not in {'y', 'yes', 'true', 't', '1'}:
    raise OneoffError('User aborted run')
