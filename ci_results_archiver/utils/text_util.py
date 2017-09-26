# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Text utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import re

_TIME_RE = re.compile(
    r'^(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s)?$')


def ParseTimeDelta(timedelta_str):
  """Parses a string representing a time delta.

  "1h5m30s" -> datetime.timedelta(hours=1, minutes=5, seconds=30)

  Args:
    timedelta_str: A string representing a time delta.

  Returns:
    datetime.timedelta object.

  Raises:
    ValueError: On parse errors.
  """
  match = _TIME_RE.search(timedelta_str)
  if not match or not timedelta_str:
    raise ValueError('Unknown timedelta spec: %s' % timedelta_str)
  timedelta_kwargs = {
      key: int(value)
      for key, value in match.groupdict().iteritems() if value
  }
  return datetime.timedelta(**timedelta_kwargs)  # pylint: disable=star-args
