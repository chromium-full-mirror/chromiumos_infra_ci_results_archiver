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
from google.cloud import storage  # pylint: disable=import-error,no-name-in-module
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
    self._storage_client = mock.Mock(storage.Client)
    self._bucket = self._storage_client.bucket.return_value

    self._wrapper = bigquery_wrapper.BigQueryWrapper(
        bigquery_client=self._bigquery_client,
        dataset=self._dataset,
        storage_client=self._storage_client,
        bucket=self._bucket)

  def testTableExists(self):
    """TableExists() works."""
    self._dataset.table('ds').exists.return_value = True
    self.assertTrue(self._wrapper.TableExists('ds'))

  def testListTableNames(self):
    """ListTableNames() works."""
    datasets = [mock.Mock(bigquery.Dataset) for _ in range(5)]
    datasets[0].name = 'cherry'
    datasets[1].name = 'apricot'
    datasets[2].name = 'banana'
    datasets[3].name = 'apple'
    datasets[4].name = 'cinnamon'
    self._dataset.list_tables.return_value = datasets

    self.assertEqual(['apple', 'apricot', 'banana', 'cherry', 'cinnamon'],
                     self._wrapper.ListTableNames())

  def testRunQuery(self):
    """RunQuery() works in a normal case."""
    results = self._bigquery_client.run_sync_query.return_value
    results.complete = True
    results.rows = [['a', 'b'], ['c', 'd']]
    results.page_token = None
    results.total_bytes_processed = 0

    rows = self._wrapper.RunQuery(
        query='query', timeout_seconds=3, description='description', params=())

    self._bigquery_client.run_sync_query.assert_called_once_with(
        'query', query_parameters=())

    self.assertEqual([['a', 'b'], ['c', 'd']], rows)

  def testRunQueryMultiPageResponse(self):
    """RunQuery() handles multi-page response."""
    results = self._bigquery_client.run_sync_query.return_value
    results.complete = True
    results.rows = [['a', 'b']]
    results.page_token = 'token'
    results.total_bytes_processed = 0

    def FetchDataSideEffect(page_token):
      """Implements QueryResults.fetch_data()."""
      if page_token == 'token':
        return FakeFetchDataIterable('token2', [['c', 'd']])
      if page_token == 'token2':
        return FakeFetchDataIterable(None, [['e', 'f']])
      assert False

    results.fetch_data.side_effect = FetchDataSideEffect

    rows = self._wrapper.RunQuery(
        query='query', timeout_seconds=3, description='description', params=())

    self._bigquery_client.run_sync_query.assert_called_once_with(
        'query', query_parameters=())

    self.assertEqual([['a', 'b'], ['c', 'd'], ['e', 'f']], rows)

  def testRunQueryError(self):
    """RunQuery() aborts on errors."""
    results = self._bigquery_client.run_sync_query.return_value
    results.complete = False
    results.errors = [{'message': 'error'}]

    with self.assertRaises(bigquery_wrapper.BigQueryError):
      self._wrapper.RunQuery(
          query='query',
          timeout_seconds=3,
          description='description',
          params=())

  def testLoadEntries(self):
    """LoadEntries() works in a normal case."""
    self._bucket.name = 'bucket'
    self._dataset.name = 'dataset'

    uploaded_contents = []

    def UploadSideEffect(content):
      """Implements Blob.upload_from_string()."""
      uploaded_contents.append(content)

    blob = self._bucket.blob.return_value
    blob.upload_from_string.side_effect = UploadSideEffect

    job = self._bigquery_client.load_table_from_storage.return_value
    job.state = 'DONE'
    job.error_result = None

    self._dataset.table('table').schema = []
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
    self._wrapper.LoadEntries('table', schema, entries, job_name='job_name')

    self._bucket.blob.assert_called_once_with(
        'loads/dataset/job_name/data.json')
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

    self._bigquery_client.load_table_from_storage.assert_called_once_with(
        'job_name',
        self._dataset.table('table'),
        'gs://bucket/loads/dataset/job_name/data.json')
    self.assertEqual(job.create_disposition, 'CREATE_IF_NEEDED')
    self.assertEqual(job.write_disposition, 'WRITE_APPEND')
    self.assertEqual(job.source_format, 'NEWLINE_DELIMITED_JSON')
    self.assertEqual(job.schema, schema)
    job.begin.assert_called_once()

  def testLoadEntriesError(self):
    """LoadEntries() aborts on errors."""
    self._bucket.name = 'bucket'
    self._dataset.name = 'dataset'
    self._dataset.table('table').schema = []

    job = self._bigquery_client.load_table_from_storage.return_value
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
    self._dataset.name = 'dataset'
    self._dataset.table('table').schema = []

    job = self._bigquery_client.load_table_from_storage.return_value
    job.state = 'DONE'
    job.error_result = None

    schema = ['new_column']
    entries = []
    self._wrapper.LoadEntries('table', schema, entries, job_name='job_name')
    self._dataset.table('table').patch.assert_called_once_with(
        mock.ANY, schema=['new_column'])


class FakeFetchDataIterable(list):
  """Fake iterable object returned by QueryResults.fetch_data()."""

  def __init__(self, next_page_token, values):
    """Constructor."""
    super(FakeFetchDataIterable, self).__init__(values)
    self.next_page_token = next_page_token
