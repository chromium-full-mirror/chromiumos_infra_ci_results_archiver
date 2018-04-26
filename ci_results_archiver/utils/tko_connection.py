# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Connection to TKO DB."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# MySQL query used to retrieve the largest TKO job ID.
_TKO_JOB_LARGEST_ID_QUERY = """
SELECT
  job_idx AS tko_job_id
FROM
  tko_jobs
ORDER BY
  job_idx DESC
LIMIT 1
;
"""

# MySQL query used to retrieve TKO jobs.
_TKO_JOBS_QUERY = """
SELECT
  j.job_idx AS tko_job_id,
  j.afe_job_id,
  j.afe_parent_job_id,
  j.username,
  j.suite,
  j.queued_time AS queued_time,
  j.started_time AS started_time,
  j.finished_time AS finished_time,
  j.build,
  j.build_version,
  j.board,
  m.hostname,
  j.label,
  j.tag
FROM
  (
    SELECT *
    FROM tko_jobs
    WHERE job_idx >= %(tko_job_id_start)s
    ORDER BY job_idx ASC
    LIMIT %(limit)s
  ) AS j
  LEFT OUTER JOIN
    tko_machines AS m
    ON m.machine_idx = j.machine_idx
;
"""

# MySQL query used to retrieve TKO jobs' task references.
_TKO_TASK_REFERENCE_QUERY = """
SELECT
  t.tko_job_idx as tko_job_id,
  t.reference_type,
  t.task_id,
  t.parent_task_id
FROM tko_task_references t
WHERE tko_job_idx in %(tko_job_ids)s
;
"""
# MySQL query used to retrieve TKO tests.
_TKO_TESTS_QUERY = """
SELECT
  t.job_idx AS tko_job_id,
  t.test_idx AS tko_test_id,
  t.test,
  s.word AS status,
  t.started_time AS started_time,
  t.finished_time AS finished_time,
  t.reason,
  m.hostname,
  t.subdir,
  t.invalid,
  t.invalidates_test_idx AS invalidating_tko_test_id
FROM
  (
    SELECT *
    FROM tko_tests
    WHERE job_idx IN %(tko_job_ids)s
  ) AS t
  LEFT OUTER JOIN
    tko_status AS s
    ON s.status_idx = t.status
  LEFT OUTER JOIN
    tko_machines AS m
    ON m.machine_idx = t.machine_idx
;
"""

# MySQL query used to retrieve TKO job keyvals.
_TKO_JOB_KEYVALS_QUERY = """
SELECT
  job_id AS tko_job_id,
  `key`,
  value
FROM
  tko_job_keyvals
WHERE
  job_id in %(tko_job_ids)s AND
  -- Drop excessive keyvals. In suite jobs, these MD5-hash keyvals record AFE
  -- job IDs of child test jobs, but afe_parent_job_id is enough for us.
  NOT `key` REGEXP '^[0-9a-f]{32}$'
;
"""


class TkoConnection(object):
  """Connection to TKO DB.

  This is a thin wrapper of MySQLWrapper specialized for TKO DB.
  """

  def __init__(self, mysql_wrapper):
    """Initializes the connection.

    Args:
      mysql_wrapper: MySQLWrapper object for TKO DB.
    """
    self._mysql_wrapper = mysql_wrapper

  def QueryLargestJobId(self):
    """Retrieves the largest TKO job ID from the TKO database.

    Returns:
      A TKO job ID.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    return self._mysql_wrapper.RunQuery(
        query=_TKO_JOB_LARGEST_ID_QUERY,
        description='Getting the largest TKO job ID')[0]['tko_job_id']

  def QueryJobs(self, tko_job_id_start, limit):
    """Retrieves TKO job rows from the TKO database.

    Rows are returned by the ascending order of the ID.

    Args:
      tko_job_id_start: Minimum TKO job ID.
      limit: Maximum number of rows returned.

    Returns:
      A list of dictionaries representing TKO job rows.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    return self._mysql_wrapper.RunQuery(
        query=_TKO_JOBS_QUERY,
        params={
            'tko_job_id_start': tko_job_id_start,
            'limit': limit,
        },
        description='Dumping TKO jobs')

  def QueryJobKeyvals(self, tko_job_ids):
    """Retrieves TKO job keyval rows from the TKO database.

    Args:
      tko_job_ids: A list of TKO job ids to retrieve keyvals of.

    Returns:
      A list of dictionaries representing TKO job keyval rows.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    return self._mysql_wrapper.RunQuery(
        query=_TKO_JOB_KEYVALS_QUERY,
        params={'tko_job_ids': tko_job_ids},
        description='Dumping TKO job keyvals')

  def QueryTests(self, tko_job_ids):
    """Retrieves TKO test rows from the TKO database.

    Args:
      tko_job_ids: A list of TKO job ids to retrieve test entries of.

    Returns:
      A list of dictionaries representing TKO test rows.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    return self._mysql_wrapper.RunQuery(
        query=_TKO_TESTS_QUERY,
        params={'tko_job_ids': tko_job_ids},
        description='Dumping TKO tests')

  def QueryTaskReferences(self, tko_job_ids):
    """Retrieves TKO task references from the TKO database.

    Args:
      tko_job_ids: A list of TKO job ids to retrieve task references for.

    Returns:
      A list of dictionaries representing task references.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    return self._mysql_wrapper.RunQuery(
        query=_TKO_TASK_REFERENCE_QUERY,
        params={'tko_job_ids': tko_job_ids},
        description='Dumping TKO task references')
