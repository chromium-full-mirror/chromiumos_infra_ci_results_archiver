# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for afe_job_importer."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import unittest

import pytz

from ci_results_archiver.importers import afe_job_importer
from ci_results_archiver.importers import grace_period
from ci_results_archiver.utils.test import fake_afe_connection

_DEFAULT_GRACE_PERIOD = grace_period.GracePeriod(
    id_column='afe_job_id',
    insertion_timestamp_column='created_on',
    timeout=None,
    capacity=0)


class AfeJobImporterTestCase(unittest.TestCase):
  """Unit tests for AfeJobImporter."""

  def testNormal(self):
    """ImportEntries() works in a usual case."""
    afe = fake_afe_connection.FakeAfeConnection(
        jobs=[
            _CreateAfeJobRow(1000),
            _CreateAfeJobRow(1001),
            _CreateAfeJobRow(1002),
        ],
        job_keyvals=[
            _CreateAfeJobKeyvalRow(1000, 'B', 'banana'),
            _CreateAfeJobKeyvalRow(1000, 'A', 'apple'),
            _CreateAfeJobKeyvalRow(1002, 'A', 'apricot'),
        ],
        job_dependency_labels=[
            _CreateAfeJobDependencyLabelRow(1000, 'pool:pvt'),
            _CreateAfeJobDependencyLabelRow(1000, 'board:samus'),
            _CreateAfeJobDependencyLabelRow(1001, 'board:link'),
        ])
    importer = afe_job_importer.AfeJobImporter(
        afe=afe, max_entries=10, grace_period=_DEFAULT_GRACE_PERIOD)
    entries, modify_ids = importer.ImportEntries(next_id=1000)

    self.assertEquals([
        {
            'afe_job_id': 1000,
            'afe_parent_job_id': 123,
            'owner': 'someone',
            'name': 'jobname',
            'priority': 234,
            'control_file': 'abcdefg',
            'control_type': 'SERVER',
            'created_on': datetime.datetime.fromtimestamp(1234567890, pytz.utc),
            'synch_count': 345,
            'run_verify': 1,
            'run_reset': 1,
            'timeout_mins': 456,
            'max_runtime_mins': 567,
            'reboot_before': 'NEVER',
            'reboot_after': 'NEVER',
            'parse_failed_repair': 1,
            'test_retry': 678,
            'shard': 'some.shard',
            'require_ssp': 1,
            'keyvals': [
                {'key': 'A', 'value': 'apple'},
                {'key': 'B', 'value': 'banana'},
            ],
            'dependency_labels': ['board:samus', 'pool:pvt'],
        },
        {
            'afe_job_id': 1001,
            'afe_parent_job_id': 123,
            'owner': 'someone',
            'name': 'jobname',
            'priority': 234,
            'control_file': 'abcdefg',
            'control_type': 'SERVER',
            'created_on': datetime.datetime.fromtimestamp(1234567890, pytz.utc),
            'synch_count': 345,
            'run_verify': 1,
            'run_reset': 1,
            'timeout_mins': 456,
            'max_runtime_mins': 567,
            'reboot_before': 'NEVER',
            'reboot_after': 'NEVER',
            'parse_failed_repair': 1,
            'test_retry': 678,
            'shard': 'some.shard',
            'require_ssp': 1,
            'keyvals': [],
            'dependency_labels': ['board:link'],
        },
        {
            'afe_job_id': 1002,
            'afe_parent_job_id': 123,
            'owner': 'someone',
            'name': 'jobname',
            'priority': 234,
            'control_file': 'abcdefg',
            'control_type': 'SERVER',
            'created_on': datetime.datetime.fromtimestamp(1234567890, pytz.utc),
            'synch_count': 345,
            'run_verify': 1,
            'run_reset': 1,
            'timeout_mins': 456,
            'max_runtime_mins': 567,
            'reboot_before': 'NEVER',
            'reboot_after': 'NEVER',
            'parse_failed_repair': 1,
            'test_retry': 678,
            'shard': 'some.shard',
            'require_ssp': 1,
            'keyvals': [
                {'key': 'A', 'value': 'apricot'},
            ],
            'dependency_labels': [],
        },
    ], entries)
    self.assertEquals([], modify_ids)

  def testImportRange(self):
    """ImportEntries() handles next_id and max_entries."""
    afe = fake_afe_connection.FakeAfeConnection(jobs=[
        _CreateAfeJobRow(1000),
        _CreateAfeJobRow(1001),
        _CreateAfeJobRow(1002),
        _CreateAfeJobRow(1003),
        _CreateAfeJobRow(1004),
        _CreateAfeJobRow(1005),
    ])
    importer = afe_job_importer.AfeJobImporter(
        afe=afe, max_entries=2, grace_period=_DEFAULT_GRACE_PERIOD)
    entries, _ = importer.ImportEntries(next_id=1003)

    self.assertEquals(2, len(entries))
    self.assertEquals(1003, entries[0]['afe_job_id'])
    self.assertEquals(1004, entries[1]['afe_job_id'])

  def testNoEntries(self):
    """ImportEntries() works even if there is no entry to import."""
    afe = fake_afe_connection.FakeAfeConnection()
    importer = afe_job_importer.AfeJobImporter(
        afe=afe, max_entries=10, grace_period=_DEFAULT_GRACE_PERIOD)
    entries, _ = importer.ImportEntries(next_id=1000)

    self.assertEquals(0, len(entries))


def _CreateAfeJobRow(
    afe_job_id,
    afe_parent_job_id=123,
    owner='someone',
    name='jobname',
    priority=234,
    control_file='abcdefg',
    control_type=1,  # SERVER
    created_on=datetime.datetime.fromtimestamp(1234567890, pytz.utc),
    synch_count=345,
    run_verify=1,  # tinyint(1), not boolean
    run_reset=1,  # smallint(6), not boolean
    timeout_mins=456,
    max_runtime_mins=567,
    reboot_before=0,  # NEVER,
    reboot_after=0,  # NEVER,
    parse_failed_repair=1,  # tinyint(1), not boolean
    test_retry=678,
    shard='some.shard',
    require_ssp=1):  # tinyint(1), not boolean
  """Creates a row dictionary for _AFE_JOBS_QUERY."""
  # pylint: disable=unused-argument
  return dict(locals())


def _CreateAfeJobKeyvalRow(afe_job_id, key, value):
  """Creates a row dictionary for _AFE_JOB_KEYVALS_QUERY."""
  # pylint: disable=unused-argument
  return dict(locals())


def _CreateAfeJobDependencyLabelRow(afe_job_id, label):
  """Creates a row dictionary for _AFE_JOB_DEPENDENCY_LABELS_QUERY."""
  # pylint: disable=unused-argument
  return dict(locals())
