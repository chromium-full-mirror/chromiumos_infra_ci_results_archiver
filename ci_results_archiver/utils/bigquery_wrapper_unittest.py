# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for bigquery_wrapper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import json
import unittest

from google.cloud import bigquery  # pylint: disable=import-error,no-name-in-module
from google.cloud.storage import bucket  # pylint: disable=import-error,no-name-in-module
from google.cloud.exceptions import NotFound # pylint: disable=import-error,no-name-in-module
import mock
import pytz

from ci_results_archiver.utils import bigquery_wrapper

PST = pytz.timezone('US/Pacific')


class BigQueryWrapperTestCase(unittest.TestCase):
  """Unit tests for BigQueryWrapper."""

  def setUp(self):
    """Setup."""
    self._bigquery_client = mock.Mock(bigquery.Client)
    self._dataset = self._bigquery_client.dataset.return_value
    self._bucket = mock.Mock(bucket.Bucket)

    self._wrapper = bigquery_wrapper.BigQueryWrapper(
        bigquery_client=self._bigquery_client,
        dataset=self._dataset,
        bucket=self._bucket)

  def testTableExists(self):
    """TableExists() works."""
    table_name = 'table'
    table_ref = 'project.dataset.table_id'
    self._dataset.table.return_value = table_ref
    table = bigquery.table.Table(table_ref, schema=[])
    self._bigquery_client.get_table.return_value = table
    self.assertTrue(self._wrapper.TableExists(table_name))
    self._dataset.table.assert_called_once_with(table_name)
    self._bigquery_client.get_table.assert_called_once_with(table_ref)

  def testListTableNames(self):
    """ListTableNames() works."""
    datasets = [mock.Mock(bigquery.Dataset) for _ in range(5)]
    datasets[0].table_id = 'cherry'
    datasets[1].table_id = 'apricot'
    datasets[2].table_id = 'banana'
    datasets[3].table_id = 'apple'
    datasets[4].table_id = 'cinnamon'
    self._bigquery_client.list_tables.return_value = datasets

    self.assertEqual(['apple', 'apricot', 'banana', 'cherry', 'cinnamon'],
                     self._wrapper.ListTableNames())

  def testRunQuery(self):
    """RunQuery() works in a normal case."""
    query_job = self._bigquery_client.query.return_value
    query_job.state = 'DONE'
    query_job.total_bytes_processed = 0
    query_job.error_result = None
    query_job.result.return_value = [['a', 'b'], ['c', 'd']]
    mock_config = bigquery.QueryJobConfig(default_dataset=self._dataset)
    with mock.patch.object(bigquery, 'QueryJobConfig',
                           return_value=mock_config):
      rows = self._wrapper.RunQuery(
          query='query', timeout_seconds=3, description='description')
      self._bigquery_client.query.assert_called_once_with(
          'query', job_config=mock_config)
      self.assertEqual([['a', 'b'], ['c', 'd']], rows)

  def testRunQueryError(self):
    """RunQuery() aborts on errors."""
    query_job = self._bigquery_client.query.return_value
    query_job.state = 'DONE'
    query_job.errors = [{'message': 'error'}]
    query_job.result.return_value = []

    with self.assertRaises(bigquery_wrapper.BigQueryError):
      self._wrapper.RunQuery(
          query='query',
          timeout_seconds=3,
          description='description')

  def testLoadEntries(self):
    """LoadEntries() works in a normal case."""
    self._bucket.name = 'bucket'
    self._dataset.dataset_id = 'dataset'

    uploaded_contents = []

    def UploadSideEffect(content):
      """Implements Blob.upload_from_string()."""
      uploaded_contents.append(content)

    blob = self._bucket.blob.return_value
    blob.upload_from_string.side_effect = UploadSideEffect

    job = self._bigquery_client.load_table_from_uri.return_value
    job.state = 'DONE'
    job.error_result = None

    table_name = 'table_name'
    table_ref = 'project.dataset.table_id'
    self._dataset.table.return_value = table_ref
    table = bigquery.table.Table(table_ref, schema=[])
    self._bigquery_client.get_table.return_value = table

    schema = []
    entries = [
        {
            'id': 1,
            'fruit': 'apple',
            'time': pytz.utc.localize(datetime.datetime(2017, 9, 15, 12, 3, 4)),
        },
        {
            'id': 2,
            'fruit': 'banana',
            'time': PST.localize(datetime.datetime(2017, 9, 15, 5, 3, 4)),
        },
    ]
    mock_config = bigquery.LoadJobConfig()
    with mock.patch.object(bigquery, 'LoadJobConfig', return_value=mock_config):
      self._wrapper.LoadEntries(table_name, schema, entries, job_name='job_name')
      self._dataset.table.assert_called_with(table_name)
      self._bigquery_client.get_table.assert_called_with(table_ref)
      self.assertEqual(len(uploaded_contents), 1)
      self.assertEqual([
          {
              u'id': 1,
              u'fruit': u'apple',
              u'time': u'2017-09-15 12:03:04 UTC',
          },
          {
              u'id': 2,
              u'fruit': u'banana',
              u'time': u'2017-09-15 12:03:04 UTC',
          },
      ], [json.loads(line) for line in uploaded_contents[0].splitlines()])
      bigquery.LoadJobConfig.assert_called_once_with(
          create_disposition='CREATE_IF_NEEDED',
          schema=schema,
          source_format='NEWLINE_DELIMITED_JSON',
          write_disposition='WRITE_APPEND')
      self._bigquery_client.load_table_from_uri.assert_called_once_with(
          'gs://bucket/loads/dataset/job_name/data.json',
          table_ref,
          job_id='job_name',
          job_config=mock_config)

  def testLoadEntriesError(self):
    """LoadEntries() aborts on errors."""
    self._bucket.name = 'bucket'
    self._dataset.dataset_id = 'dataset'
    table_ref = 'project.dataset.table_id'
    table = bigquery.table.Table(table_ref, schema=[])
    self._bigquery_client.get_table.return_value = table

    job = self._bigquery_client.load_table_from_uri.return_value
    job.state = 'DONE'
    job.error_result = [{'message': 'error'}]

    schema = []
    entries = [
        {'id': 1, 'fruit': 'apple'},
        {'id': 2, 'fruit': 'banana'},
    ]
    with self.assertRaises(bigquery_wrapper.BigQueryError):
      self._wrapper.LoadEntries('table', schema, entries, job_name='job_name')

  def testLoadEntriesPatchTableSchema(self):
    """LoadEntries() patches table schema on new columns"""
    self._bucket.name = 'bucket'
    self._dataset.dataset_id = 'dataset'

    table_name = 'table_name'
    table_ref = 'project.dataset.table_id'
    self._dataset.table.return_value = table_ref

    table = bigquery.table.Table(table_ref, schema=[])
    self._bigquery_client.get_table.return_value = table

    job = self._bigquery_client.load_table_from_uri.return_value
    job.state = 'DONE'
    job.error_result = None

    schema = [bigquery.SchemaField("new_column", "STRING", mode="REQUIRED")]
    entries = []
    self._wrapper.LoadEntries(table_name, schema, entries, job_name='job_name')
    self._dataset.table.assert_called_with(table_name)
    self._bigquery_client.update_table.assert_called_once_with(
        table_ref, schema)

  def testLoadEntriesNoPatchNewTable(self):
    """LoadEntries() does not patch table schema on new table"""
    self._bucket.name = 'bucket'
    self._dataset.dataset_id = 'dataset'
    self._bigquery_client.get_table.side_effect = NotFound('No table found.')
    job = self._bigquery_client.load_table_from_uri.return_value
    job.state = 'DONE'
    job.error_result = None

    schema = [bigquery.SchemaField("new_column", "STRING", mode="REQUIRED")]
    entries = []
    self._wrapper.LoadEntries('table', schema, entries, job_name='job_name')
    self.assertEqual(self._dataset.table('table').patch.call_count, 0)


class FakeFetchDataIterable(list):
  """Fake iterable object returned by QueryResults.fetch_data()."""

  def __init__(self, next_page_token, values):
    """Constructor."""
    super(FakeFetchDataIterable, self).__init__(values)
    self.next_page_token = next_page_token
