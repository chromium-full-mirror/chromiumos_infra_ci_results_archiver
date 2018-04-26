# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for tko_job_importer."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import unittest

import pytz

from ci_results_archiver.importers import grace_period
from ci_results_archiver.importers import tko_job_importer
from ci_results_archiver.utils.test import fake_tko_connection

_DEFAULT_GRACE_PERIOD = grace_period.GracePeriod(
    id_column='tko_job_id',
    insertion_timestamp_column=None,
    timeout=None,
    capacity=0)


class TkoJobImporterTestCase(unittest.TestCase):
  """Unit tests for AfeJobImporter."""

  def testNormal(self):
    """ImportEntries() works in a usual case."""
    tko = fake_tko_connection.FakeTkoConnection(
        jobs=[
            _CreateTkoJobRow(1000),
            _CreateTkoJobRow(1001),
        ],
        task_references=[
            _CreateTkoTaskReferenceRow(1000, 'afe', '1', None),
            _CreateTkoTaskReferenceRow(1001, 'afe', '2', '3'),
        ],
        job_keyvals=[
            _CreateTkoJobKeyvalRow(1000, 'B', 'banana'),
            _CreateTkoJobKeyvalRow(1000, 'A', 'apple'),
            _CreateTkoJobKeyvalRow(1001, 'A', 'apricot'),
        ],
        tests=[
            _CreateTkoTestRow(10000, 1000),
            _CreateTkoTestRow(10001, 1000),
            _CreateTkoTestRow(10010, 1001),
        ])
    importer = tko_job_importer.TkoJobImporter(
        tko=tko, max_entries=10, grace_period=_DEFAULT_GRACE_PERIOD)
    entries, modify_ids, new_next_id = importer.ImportEntries(next_id=1000)

    self.assertEquals([
        {
            'tko_job_id': 1000,
            'afe_job_id': 123,
            'afe_parent_job_id': 234,
            'task_reference_type': 'afe',
            'task_id': '1',
            'parent_task_id': None,
            'username': 'someone',
            'suite': 'suitename',
            'queued_time': datetime.datetime.fromtimestamp(
                1000000000, pytz.utc),
            'started_time': datetime.datetime.fromtimestamp(
                1000000100, pytz.utc),
            'finished_time': datetime.datetime.fromtimestamp(
                1000000200, pytz.utc),
            'build': 'link/R99-9999.0.0',
            'build_version': 'R99-9999.0.0',
            'board': 'link',
            'hostname': 'somehost',
            'label': 'somelabel',
            'tag': 'sometag',
            'tests': [
                {
                    'tko_test_id': 10000,
                    'test': 'testname',
                    'status': 'GOOD',
                    'started_time': datetime.datetime.fromtimestamp(
                        1000000140, pytz.utc),
                    'finished_time': datetime.datetime.fromtimestamp(
                        1000000180, pytz.utc),
                    'reason': 'Everything went well',
                    'hostname': 'somehost',
                    'subdir': 'some/path',
                    'invalid': False,
                    'invalidating_tko_test_id': None,
                },
                {
                    'tko_test_id': 10001,
                    'test': 'testname',
                    'status': 'GOOD',
                    'started_time': datetime.datetime.fromtimestamp(
                        1000000140, pytz.utc),
                    'finished_time': datetime.datetime.fromtimestamp(
                        1000000180, pytz.utc),
                    'reason': 'Everything went well',
                    'hostname': 'somehost',
                    'subdir': 'some/path',
                    'invalid': False,
                    'invalidating_tko_test_id': None,
                },
            ],
            'keyvals': [
                {'key': 'A', 'value': 'apple'},
                {'key': 'B', 'value': 'banana'},
            ],
        },
        {
            'tko_job_id': 1001,
            'afe_job_id': 123,
            'afe_parent_job_id': 234,
            'task_reference_type': 'afe',
            'task_id': '2',
            'parent_task_id': '3',
            'username': 'someone',
            'suite': 'suitename',
            'queued_time': datetime.datetime.fromtimestamp(
                1000000000, pytz.utc),
            'started_time': datetime.datetime.fromtimestamp(
                1000000100, pytz.utc),
            'finished_time': datetime.datetime.fromtimestamp(
                1000000200, pytz.utc),
            'build': 'link/R99-9999.0.0',
            'build_version': 'R99-9999.0.0',
            'board': 'link',
            'hostname': 'somehost',
            'label': 'somelabel',
            'tag': 'sometag',
            'tests': [
                {
                    'tko_test_id': 10010,
                    'test': 'testname',
                    'status': 'GOOD',
                    'started_time': datetime.datetime.fromtimestamp(
                        1000000140, pytz.utc),
                    'finished_time': datetime.datetime.fromtimestamp(
                        1000000180, pytz.utc),
                    'reason': 'Everything went well',
                    'hostname': 'somehost',
                    'subdir': 'some/path',
                    'invalid': False,
                    'invalidating_tko_test_id': None,
                },
            ],
            'keyvals': [
                {'key': 'A', 'value': 'apricot'},
            ],
        },
    ], entries)
    self.assertEquals([], modify_ids)
    self.assertEquals(1002, new_next_id)

  def testInvalidation(self):
    """ImportEntries() processes invalidations."""
    tko = fake_tko_connection.FakeTkoConnection(
        jobs=[_CreateTkoJobRow(1000)],
        tests=[
            # 10000: Success.
            _CreateTkoTestRow(10000, 1000),
            # 10001-10002: Retried.
            _CreateTkoTestRow(10001, 1000, invalid=True),
            _CreateTkoTestRow(10002, 1000, invalidating_tko_test_id=10001),
            # 10003: Retried, but the retry entry is out of range.
            _CreateTkoTestRow(10003, 1000, invalid=True),
            # 10003-10004: Retried, but invalid flag is not yet set due to
            # non-transactional update by TKO parser.
            _CreateTkoTestRow(10004, 1000),
            _CreateTkoTestRow(10005, 1000, invalidating_tko_test_id=10004),
            # 10006-10008: Two retries.
            _CreateTkoTestRow(10006, 1000),
            _CreateTkoTestRow(10007, 1000, invalidating_tko_test_id=10006),
            _CreateTkoTestRow(10008, 1000, invalidating_tko_test_id=10007),
            # 10009: Retried test was already processed.
            _CreateTkoTestRow(10009, 1000, invalidating_tko_test_id=9999),
        ])
    importer = tko_job_importer.TkoJobImporter(
        tko=tko, max_entries=10, grace_period=_DEFAULT_GRACE_PERIOD)
    entries, modify_ids, _ = importer.ImportEntries(next_id=1000)

    self.assertEquals(1, len(entries))
    tests = entries[0]['tests']
    self.assertEquals(10, len(tests))
    self.assertEquals((10000, False), (tests[0]['tko_test_id'],
                                       tests[0]['invalid']))
    self.assertEquals((10001, True), (tests[1]['tko_test_id'],
                                      tests[1]['invalid']))
    self.assertEquals((10002, False), (tests[2]['tko_test_id'],
                                       tests[2]['invalid']))
    self.assertEquals((10003, True), (tests[3]['tko_test_id'],
                                      tests[3]['invalid']))
    self.assertEquals((10004, True), (tests[4]['tko_test_id'],
                                      tests[4]['invalid']))
    self.assertEquals((10005, False), (tests[5]['tko_test_id'],
                                       tests[5]['invalid']))
    self.assertEquals((10006, True), (tests[6]['tko_test_id'],
                                      tests[6]['invalid']))
    self.assertEquals((10007, True), (tests[7]['tko_test_id'],
                                      tests[7]['invalid']))
    self.assertEquals((10008, False), (tests[8]['tko_test_id'],
                                       tests[8]['invalid']))
    self.assertEquals((10009, False), (tests[9]['tko_test_id'],
                                       tests[9]['invalid']))
    self.assertEquals([9999], modify_ids)

  def testImportRange(self):
    """ImportEntries() handles next_id and max_entries."""
    tko = fake_tko_connection.FakeTkoConnection(jobs=[
        _CreateTkoJobRow(1000),
        _CreateTkoJobRow(1001),
        _CreateTkoJobRow(1002),
        _CreateTkoJobRow(1003),
        _CreateTkoJobRow(1004),
        _CreateTkoJobRow(1005),
    ])
    importer = tko_job_importer.TkoJobImporter(
        tko=tko, max_entries=2, grace_period=_DEFAULT_GRACE_PERIOD)
    entries, _, new_next_id = importer.ImportEntries(next_id=1003)

    self.assertEquals(2, len(entries))
    self.assertEquals(1003, entries[0]['tko_job_id'])
    self.assertEquals(1004, entries[1]['tko_job_id'])
    self.assertEquals(1005, new_next_id)

  def testNoEntries(self):
    """ImportEntries() works even if there is no entry to import."""
    tko = fake_tko_connection.FakeTkoConnection()
    importer = tko_job_importer.TkoJobImporter(
        tko=tko, max_entries=10, grace_period=_DEFAULT_GRACE_PERIOD)
    entries, _, new_next_id = importer.ImportEntries(next_id=1000)

    self.assertEquals(0, len(entries))
    self.assertEquals(1000, new_next_id)


def _CreateTkoJobRow(
    tko_job_id,
    afe_job_id=123,
    afe_parent_job_id=234,
    username='someone',
    suite='suitename',
    queued_time=datetime.datetime.fromtimestamp(1000000000, pytz.utc),
    started_time=datetime.datetime.fromtimestamp(1000000100, pytz.utc),
    finished_time=datetime.datetime.fromtimestamp(1000000200, pytz.utc),
    build='link/R99-9999.0.0',
    build_version='R99-9999.0.0',
    board='link',
    hostname='somehost',
    label='somelabel',
    tag='sometag'):
  """Creates a row dictionary for _TKO_JOBS_QUERY."""
  # pylint: disable=unused-argument
  return dict(locals())


def _CreateTkoTestRow(tko_test_id,
                      tko_job_id,
                      test='testname',
                      status='GOOD',
                      started_time=datetime.datetime.fromtimestamp(
                          1000000140, pytz.utc),
                      finished_time=datetime.datetime.fromtimestamp(
                          1000000180, pytz.utc),
                      reason='Everything went well',
                      hostname='somehost',
                      subdir='some/path',
                      invalid=False,
                      invalidating_tko_test_id=None):
  """Creates a row dictionary for _TKO_TESTS_QUERY."""
  # pylint: disable=unused-argument
  return dict(locals())


def _CreateTkoJobKeyvalRow(tko_job_id, key, value):
  """Creates a row dictionary for _TKO_JOB_KEYVALS_QUERY."""
  # pylint: disable=unused-argument
  return dict(locals())


def _CreateTkoTaskReferenceRow(tko_job_id,
                               reference_type='afe',
                               task_id=None,
                               parent_task_id=None):
  """Creates a row dictionary for _TKO_TASK_REFERENCE_QUERY."""
  # pylint: disable=unused-argument
  return dict(locals())
