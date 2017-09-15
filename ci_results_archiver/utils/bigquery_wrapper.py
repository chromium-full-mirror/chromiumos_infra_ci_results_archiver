# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Simple wrapper of Google BigQuery client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import json
import logging
import StringIO
import time

import pytz


class BigQueryError(Exception):
  """Represents errors on BigQuery backends."""

  def __init__(self, errors):
    """Constructor.

    Args:
      errors: A list of dictionaries representing errors.
    """
    super(BigQueryError, self).__init__('BigQuery query failed: %r' % errors)
    self.errors = errors


class BigQueryWrapper(object):
  """Simple wrapper of google.cloud.bigquery.Client object."""

  def __init__(self, bigquery_client, dataset, storage_client, bucket):
    """Initializes the wrapper.

    Args:
      bigquery_client: google.cloud.bigquery.Client object.
      dataset: google.cloud.bigquery.Dataset object.
      storage_client: google.cloud.storage.Client object.
      bucket: google.cloud.storage.Bucket object.
    """
    self._bigquery_client = bigquery_client
    self._dataset = dataset
    self._storage_client = storage_client
    self._bucket = bucket

  def TableExists(self, table_name):
    """Checks if the specified table exists or not.

    Args:
      table_name: Table name.

    Returns:
      True if the table exists, otherwise False.

    Raises:
      google.cloud.exceptions.GoogleCloudError: On Google Cloud errors.
    """
    return self._dataset.table(table_name).exists()

  def ListTableNames(self, prefix):
    """Retrieves a list of table names with specified prefix in the dataset.

    Args:
      prefix: A prefix string of table names.

    Returns:
      A sorted list of table names.

    Raises:
      google.cloud.exceptions.GoogleCloudError: On Google Cloud errors.
    """
    all_tables = self._dataset.list_tables()
    return sorted(
        table.name for table in all_tables if table.name.startswith(prefix))

  def RunQuery(self, query, timeout_seconds, description, params=()):
    """Runs a query.

    Args:
      query: Query string.
      timeout_seconds: Timeout in seconds.
      description: Description message explaining what this query does.
          This is used only for logging.
      params: List of query parameters.

    Returns:
      A list of tuples representing result rows.

    Raises:
      google.cloud.exceptions.GoogleCloudError: On Google Cloud errors.
      BigQueryError: On BigQuery errors.
    """
    logging.info('Running BigQuery query: %s', description)
    logging.debug('Query: %s', query)

    results = self._bigquery_client.run_sync_query(
        query, query_parameters=params)
    results.use_legacy_sql = False
    results.default_dataset = self._dataset
    results.timeout_ms = timeout_seconds * 1000

    start_time = time.time()
    results.run()

    if not results.complete:
      raise BigQueryError(results.errors)

    rows = _GetPaginatedResultRows(results)

    end_time = time.time()

    logging.info('BigQuery query successfully finished in %.3fs; '
                 'processed %d bytes, got %d rows.', end_time - start_time,
                 results.total_bytes_processed, len(rows))
    return rows

  def LoadEntries(self, table_name, schema, entries, job_name=None):
    """Loads entries into a table.

    Entries are first serialized as newline-delimited JSON and uploaded to
    Google Cloud Storage, then a load job is requested to BigQuery.

    The target table is created if it does not exist yet. Entries are always
    appended to the table and do not overwrite existing entries.

    Args:
      table_name: Table name.
      schema: Schema of the table as a list of SchemaField.
      entries: A list of dictionaries representing entries.
      job_name: If set, sets the load job name explicitly. Usually you do not
          need to set this.

    Raises:
      google.cloud.exceptions.GoogleCloudError: On Google Cloud errors.
    """
    if job_name is None:
      job_name = 'load_%s_%s_%s' % (
          self._dataset.name, table_name,
          datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S%f'))
    json_path = 'loads/%s/%s/data.json' % (self._dataset.name, job_name)

    self._UploadEntriesToGs(entries, json_path)
    job = self._CreateLoadJobFromGs(json_path, schema, table_name, job_name)
    self._StartAndWaitForLoadJobCompletion(job)

  def _UploadEntriesToGs(self, entries, json_path):
    """Uploads entries to Google Cloud Storage as a newline-delimited JSON.

    Args:
      entries: A list of dictionaries representing entries.
      json_path: Path to a new JSON file, relative from Google Cloud Storage
          bucket root.
    """
    entries_json = _SerializeToNewlineDelimitedJson(entries)
    logging.info('Uploading %d entries to GCS', len(entries))
    self._bucket.blob(json_path).upload_from_string(entries_json)

  def _CreateLoadJobFromGs(self, json_path, schema, table_name, job_name):
    """Creates a new load job that imports entries from Google Cloud Storage.

    Args:
      json_path: Path to a JSON file, relative from Google Cloud Storage
          bucket root.
      schema: Schema of the table as a list of SchemaField.
      table_name: Name of a BigQuery table to insert new entries to.
      job_name: Unique name of a load job.

    Returns:
      google.cloud.bigquery.job.LoadTableFromStorageJob object.
    """
    json_url = 'gs://%s/%s' % (self._bucket.name, json_path)
    job = self._bigquery_client.load_table_from_storage(
        job_name, self._dataset.table(table_name), json_url)
    job.create_disposition = 'CREATE_IF_NEEDED'
    job.write_disposition = 'WRITE_APPEND'
    job.source_format = 'NEWLINE_DELIMITED_JSON'
    job.schema = schema
    return job

  def _StartAndWaitForLoadJobCompletion(self, job):
    """Starts a load job and waits for it to finish.

    Args:
      job: google.cloud.bigquery.job.LoadTableFromStorageJob object.

    Raises:
      BigQueryError: On backend errors.
    """
    start_time = time.time()
    job.begin()
    logging.info('Started a job "%s" to load entries into %s.%s', job.name,
                 job.destination.dataset_name, job.destination.name)

    while True:
      job.reload()
      logging.debug('Job state: %s', job.state)
      if job.state == 'DONE':
        if job.error_result:
          raise BigQueryError(job.errors)
        break
      time.sleep(1)

    end_time = time.time()
    logging.info('Load successfully finished in %.3fs.', end_time - start_time)


def _SerializeToNewlineDelimitedJson(entries):
  """Serializes entries into a newline-delimited JSON.

  Args:
    entries: A list of dictionaries representing entries.

  Returns:
    UTF-8 encoded string of a newline-delimited JSON.
  """
  buf = StringIO.StringIO()
  for entry in entries:
    json.dump(entry, buf, separators=(',', ':'), default=_CustomEncoder)
    buf.write('\n')
  return buf.getvalue().encode('utf-8')


def _CustomEncoder(value):
  """Custom JSON value encoder to format timezone-aware datetime values.

  Args:
    value: Any object.

  Returns:
    A serialized string.

  Raises:
    TypeError: On failure.
  """
  if isinstance(value, datetime.datetime):
    if value.tzinfo is None:
      raise TypeError('Naive datetime can not be serialized')
    utc_datetime = value.astimezone(pytz.utc)
    return utc_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')
  raise TypeError('Could not encode to JSON: %r' % value)


def _GetPaginatedResultRows(results):
  """Handles paginated results to build a list of all rows.

  Args:
    results: bigquery.QueryResults object.

  Returns:
    A list of query result rows.
  """
  rows = results.rows
  page_token = results.page_token
  while page_token:
    rows_iter = results.fetch_data(page_token=page_token)
    rows += list(rows_iter)
    page_token = rows_iter.next_page_token
  return rows
