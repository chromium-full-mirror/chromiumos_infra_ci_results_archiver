# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for text_util."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import unittest

from ci_results_archiver.utils import text_util


class TextUtilTestCase(unittest.TestCase):
  """Unit tests for text_util."""

  def testParseTimeDelta(self):
    """ParseTimeDelta() works."""
    self.assertEquals(
        datetime.timedelta(hours=10), text_util.ParseTimeDelta('10h'))
    self.assertEquals(
        datetime.timedelta(minutes=10), text_util.ParseTimeDelta('10m'))
    self.assertEquals(
        datetime.timedelta(seconds=10), text_util.ParseTimeDelta('10s'))
    self.assertEquals(
        datetime.timedelta(hours=1, minutes=5, seconds=30),
        text_util.ParseTimeDelta('1h5m30s'))

  def testParseTimeDeltaFail(self):
    """ParseTimeDelta() raises exception on parse errors."""
    with self.assertRaises(ValueError):
      text_util.ParseTimeDelta('')
    with self.assertRaises(ValueError):
      text_util.ParseTimeDelta('s')
