# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for grace_period."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import unittest

import pytz

from ci_results_archiver.importers import grace_period as grace_period_lib


class GracePeriodTestCase(unittest.TestCase):
  """Unit tests for GracePeriod."""

  def testGracePeriodTime(self):
    """Filters by grace_period_time."""
    now = _CreateDateTime(2000)
    grace_period = _CreateGracePeriod(timeout=datetime.timedelta(seconds=980))
    input_entries = [
        {'id': 1000, 'time': _CreateDateTime(1000)},
        {'id': 1010, 'time': _CreateDateTime(1010)},
        {'id': 1020, 'time': _CreateDateTime(1020)},
        {'id': 1030, 'time': _CreateDateTime(1030)},
    ]
    expected_entries = [
        {'id': 1000, 'time': _CreateDateTime(1000)},
        {'id': 1010, 'time': _CreateDateTime(1010)},
    ]
    self.assertEquals(expected_entries,
                      grace_period.FilterEntries(input_entries, now=now))

  def testGracePeriodSize(self):
    """Filters by grace_period_size."""
    grace_period = _CreateGracePeriod(capacity=3)
    input_entries = [
        {'id': 1000},
        {'id': 1010},
        {'id': 1020},
        {'id': 1030},
    ]
    expected_entries = [
        {'id': 1000},
        {'id': 1010},
    ]
    self.assertEquals(expected_entries,
                      grace_period.FilterEntries(input_entries))

  def testFirstEntryAssumedAfterSkip(self):
    """This first entry is assumed to be after skips."""
    grace_period = _CreateGracePeriod(capacity=10)
    input_entries = [
        {'id': 1000},
        {'id': 1010},
        {'id': 1020},
        {'id': 1030},
    ]
    expected_entries = []
    self.assertEquals(expected_entries,
                      grace_period.FilterEntries(input_entries))

  def testNoSkip(self):
    """Works when there is no skip."""
    now = _CreateDateTime(2000)
    grace_period = _CreateGracePeriod(
        capacity=3, timeout=datetime.timedelta(seconds=10000))
    input_entries = [
        {'id': 1000, 'time': _CreateDateTime(1000)},
        {'id': 1001, 'time': _CreateDateTime(1001)},
        {'id': 1002, 'time': _CreateDateTime(1002)},
        {'id': 1003, 'time': _CreateDateTime(1003)},
    ]
    expected_entries = [
        {'id': 1000, 'time': _CreateDateTime(1000)},
        {'id': 1001, 'time': _CreateDateTime(1001)},
        {'id': 1002, 'time': _CreateDateTime(1002)},
        {'id': 1003, 'time': _CreateDateTime(1003)},
    ]
    self.assertEquals(expected_entries,
                      grace_period.FilterEntries(input_entries, now=now))

  def testAllSkipsDismissed(self):
    """There are skips, but all of them are dismissed."""
    now = _CreateDateTime(2000)
    grace_period = _CreateGracePeriod(
        capacity=3, timeout=datetime.timedelta(seconds=900))
    input_entries = [
        # First assumed skip is dismissed by grace_period_size.
        {'id': 1000, 'time': _CreateDateTime(1000)},
        {'id': 1001, 'time': _CreateDateTime(1010)},
        # Skip of 1002 is dismissed by grace_period_size. Note that clock skew
        # happened here!
        {'id': 1003, 'time': _CreateDateTime(1999)},
        {'id': 1004, 'time': _CreateDateTime(1040)},
        # Skip of 1005 is dismissed by grace_period_time.
        {'id': 1006, 'time': _CreateDateTime(1060)},
        {'id': 1007, 'time': _CreateDateTime(1070)},
    ]
    expected_entries = [
        {'id': 1000, 'time': _CreateDateTime(1000)},
        {'id': 1001, 'time': _CreateDateTime(1010)},
        {'id': 1003, 'time': _CreateDateTime(1999)},
        {'id': 1004, 'time': _CreateDateTime(1040)},
        {'id': 1006, 'time': _CreateDateTime(1060)},
        {'id': 1007, 'time': _CreateDateTime(1070)},
    ]
    self.assertEquals(expected_entries,
                      grace_period.FilterEntries(input_entries, now=now))

  def testUnsorted(self):
    """Works with unsorted entries."""
    grace_period = _CreateGracePeriod(capacity=3)
    input_entries = [
        {'id': 1030},
        {'id': 1010},
        {'id': 1000},
        {'id': 1020},
    ]
    expected_entries = [
        {'id': 1000},
        {'id': 1010},
    ]
    self.assertEquals(expected_entries,
                      grace_period.FilterEntries(input_entries))


def _CreateGracePeriod(timeout=None, capacity=None):
  """Helper to create a GracePeriod object."""
  return grace_period_lib.GracePeriod(
      id_column='id',
      insertion_timestamp_column='time',
      timeout=timeout,
      capacity=capacity)


def _CreateDateTime(timestamp):
  """Helper to create a datetime object from a timestamp."""
  return datetime.datetime.fromtimestamp(timestamp, pytz.utc)
