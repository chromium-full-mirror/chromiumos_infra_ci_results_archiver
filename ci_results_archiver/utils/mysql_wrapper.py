# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Simple wrapper of MySQL db."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import time

from chromite.lib import retry_util
import MySQLdb
import MySQLdb.constants
import MySQLdb.converters
import MySQLdb.cursors
import pytz

_DEFAULT_DATETIME_CONVERTER = MySQLdb.converters.conversions[
    MySQLdb.constants.FIELD_TYPE.DATETIME]
_DEFAULT_TIMESTAMP_CONVERTER = MySQLdb.converters.conversions[
    MySQLdb.constants.FIELD_TYPE.TIMESTAMP]


class MySQLWrapper(object):
  """Simple wrapper of MySQLdb.

  An important feature of this wrapper is DATETIME conversion. When MySQLdb
  returns DATETIME values, it converts them to UTC datetime objects
  according to timezone given in the constructor. TIMESTAMP values are also
  converted to UTC datetime objects.
  """

  def __init__(self, hostname, username, password, database, timezone):
    """Connects to the database.

    Args:
      hostname: MySQL server hostname.
      username: MySQL server username.
      password: MySQL server password.
      database: MySQL server database name.
      timezone: pytz.timezone object to use for converting datetime values.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    self._hostname = hostname
    self._username = username
    self._password = password
    self._database = database
    self._timezone = timezone
    self._conversions = MySQLdb.converters.conversions.copy()
    self._conversions.update({
        MySQLdb.constants.FIELD_TYPE.DATETIME: self._ConvertDatetime,
        MySQLdb.constants.FIELD_TYPE.TIMESTAMP: self._ConvertTimestamp,
    })
    self._Reconnect()

  def RunQuery(self, query, description, params=()):
    """Runs a query.

    Args:
      query: Query string.
      description: Description message explaining what this query does.
          This is used only for logging.
      params: List of query parameters.

    Returns:
      A list of dictionaries representing result rows.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    logging.info('Running MySQL query: %s', description)
    query_str = query % params if params else query
    logging.debug('Query: %s', query_str)

    def DoRunQuery():
      """Actually runs a query."""
      cursor = self._conn.cursor(MySQLdb.cursors.DictCursor)
      cursor.execute(query, params)
      return list(cursor.fetchall())

    def HandleException(exception):
      """Handles an exception raised in DoRunQuery()."""
      # pylint: disable=no-member
      # pylint can not find MySQLdb.OperationalError because it is in a
      # C extension.
      if (isinstance(exception, MySQLdb.OperationalError) and
          exception.args[0] == 2006):
        # 2006: MySQL server has gone away. Reconnect and retry the query.
        logging.warning('MySQL server has gone away. Reconnecting.')
        self._Reconnect()
        return True
      return False

    start_time = time.time()
    rows = retry_util.GenericRetry(
        handler=HandleException, max_retry=3, functor=DoRunQuery)
    end_time = time.time()

    logging.info('MySQL query successfully finished in %.3fs; got %d rows.',
                 end_time - start_time, len(rows))
    return rows

  def _Reconnect(self):
    """Reconnects to the server.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    self._conn = MySQLdb.connect(
        host=self._hostname,
        user=self._username,
        passwd=self._password,
        db=self._database,
        charset='utf8',
        use_unicode=True,
        conv=self._conversions)
    # Set session timezone to UTC.
    self._conn.cursor().execute('SET time_zone = "+0:00"')

  def _ConvertDatetime(self, mysql_value):
    """Converts MySQL DATETIME value to UTC datetime object.

    Args:
      mysql_value: MySQL DATETIME value.

    Returns:
      UTC datetime object.
    """
    # First, use the default converter to convert the MySQL value to
    # datetime.
    naive_local_datetime = _DEFAULT_DATETIME_CONVERTER(mysql_value)
    if naive_local_datetime is None:
      return None
    aware_local_datetime = self._timezone.localize(naive_local_datetime)
    return aware_local_datetime.astimezone(pytz.utc)

  def _ConvertTimestamp(self, mysql_value):
    """Converts MySQL TIMESTAMP value to UTC datetime object.

    Args:
      mysql_value: MySQL TIMESTAMP value.

    Returns:
      Numeric timestamp value.
    """
    # First, use the default converter to convert the MySQL value to
    # datetime.
    naive_utc_datetime = _DEFAULT_TIMESTAMP_CONVERTER(mysql_value)
    if naive_utc_datetime is None:
      return None
    return pytz.utc.localize(naive_utc_datetime)
