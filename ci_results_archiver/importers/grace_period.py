# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Defines the period to wait until a new database entry to appear."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime

import pytz


class GracePeriod(object):
  """Defines the period to wait until a new database entry to appear.

  Imported database rows have autoincrement integer primary keys. This means
  their primary keys are usually contiguous, but not always. For example,
  a row with ID=7 might be committed after a row with ID=8 is committed if the
  transaction for ID=7 takes more time than that for ID=8. If we scan the table
  during such concurrent transactions, we observe an "ID skip".

  We have two notable reasons to observe ID skips: concurrent transactions and
  rolled-back transactions. For the former case, ID skips will be eventually
  filled, but for the latter case, ID skips will remain forever.

  In order not to drop rows, on encountering ID skips, importers will wait
  for them to be filled for some time ("grace period"). While waiting,
  importers will not process rows after the ID skips.

  Grace period is defined by two constraints: timeout and capacity.

    1. timeout: A duration. If the insertion timestamp of the row next to an ID
       skip is older than this, we assume it will never be filled.
    2. capacity: A number. If the number of committed rows after an ID skip is
       more than this number, we assume it will never be filled.

  A valid grace period has at least one valid constraint set.

  Note that, whenever possible, timeout constraint should be preferred over
  capacity constraint because it is difficult to guess the maximum rate of
  insertion.
  """

  def __init__(self, id_column, insertion_timestamp_column, timeout, capacity):
    """Constructs a grace period object.

    Args:
      id_column: Name of the ID column.
      insertion_timestamp_column: Name of the insertion timestamp column.
      timeout: datetime.timedelta object specifying the grace period timeout.
          This can be None.
      capacity: The number of entries specifying the grace period capacity.
          This can be None.
    """
    # At least one of the constraints must be valid.
    assert timeout is not None or capacity is not None
    self._id_column = id_column
    self._insertion_timestamp_column = insertion_timestamp_column
    self._timeout = timeout
    self._capacity = capacity

  def FilterEntries(self, entries, now=None):
    """Filters out entries in the grace period.

    This method must be called in AbstractImporter implementations.

    Args:
      entries: A list of dictionaries representing entries.
      now: The current datetime. If not given, the system time is used.

    Returns:
      A list of filtered entries.
    """
    if now is None:
      now = datetime.datetime.now(pytz.utc)

    entries = sorted(entries, key=lambda e: e[self._id_column])
    num_entries = len(entries)

    for i, entry in enumerate(entries):
      # Check if this entry is just after skips. For the first entry, we always
      # assume it is after skips for safety.
      if (i == 0 or
          entry[self._id_column] - entries[i - 1][self._id_column] != 1):
        if not self._IsGracePeriodFinished(entry, num_entries - i, now):
          return entries[:i]
    return entries

  def _IsGracePeriodFinished(self, next_entry, num_following_entries, now):
    """Checks if grace period for a skip has finished.

    Args:
      next_entry: The first committed entry after a skip.
      num_following_entries: The number of committed entries after a skip.
      now: The current datetime.

    Returns:
      True if grace period has finished.
    """
    if (self._timeout is not None and
        next_entry[self._insertion_timestamp_column] < now - self._timeout):
      return True
    if self._capacity is not None and num_following_entries >= self._capacity:
      return True
    return False
