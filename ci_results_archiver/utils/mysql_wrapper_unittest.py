# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for mysql_wrapper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest

import mock
import MySQLdb
import MySQLdb.cursors
import pytz

from ci_results_archiver.utils import mysql_wrapper


class MySQLWrapperTestCase(unittest.TestCase):
  """Unit tests for MySQLWrapper."""

  def setUp(self):
    """Setup."""
    with mock.patch('MySQLdb.connect') as connect:
      self._wrapper = mysql_wrapper.MySQLWrapper(
          hostname='hostname',
          username='username',
          password='password',
          database='database',
          timezone=pytz.timezone('Asia/Tokyo'))

      self._conn = connect.return_value

    self._cursor = self._conn.cursor()

    self._cursor.execute.assert_called_with('SET time_zone = "+0:00"')

  def testRunQuery(self):
    """RunQuery() works."""
    self._cursor.fetchall.return_value = [
        {
            'id': 1,
            'fruit': 'apple'
        },
        {
            'id': 2,
            'fruit': 'banana'
        },
    ]

    rows = self._wrapper.RunQuery('query', 'description', params=('a', 'b'))

    self._conn.cursor.assert_called_with(MySQLdb.cursors.DictCursor)
    self._cursor.execute.assert_called_with('query', ('a', 'b'))
    self.assertEqual(rows, [
        {
            'id': 1,
            'fruit': 'apple'
        },
        {
            'id': 2,
            'fruit': 'banana'
        },
    ])

  def testConvertDatetime(self):
    """Tests _ConvertDatetime() internal function."""
    # pylint: disable=protected-access
    # Asia/Tokyo is UTC+9.
    self.assertEqual(
        self._wrapper._ConvertDatetime('2017-04-01 12:00:00'),
        1491015600)  # 2017-04-01 03:00:00 UTC
    self.assertEqual(self._wrapper._ConvertDatetime('NULL'), None)

  def testConvertTimestamp(self):
    """Tests _ConvertTimestamp() internal function."""
    # pylint: disable=protected-access
    self.assertEqual(
        self._wrapper._ConvertTimestamp('2017-04-01 12:00:00'),
        1491048000)  # 2017-04-01 12:00:00 UTC
    self.assertEqual(self._wrapper._ConvertDatetime('NULL'), None)
