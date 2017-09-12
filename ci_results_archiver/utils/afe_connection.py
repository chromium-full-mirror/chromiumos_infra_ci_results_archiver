# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Connection to AFE DB."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# MySQL query used to retrieve AFE jobs.
_AFE_JOBS_QUERY = """
SELECT
  j.id AS afe_job_id,
  j.parent_job_id AS afe_parent_job_id,
  j.owner,
  j.name,
  j.priority,
  j.control_file,
  j.control_type,
  j.created_on,
  j.synch_count,
  j.run_verify,
  j.run_reset,
  j.timeout_mins,
  j.max_runtime_mins,
  j.reboot_before,
  j.reboot_after,
  j.parse_failed_repair,
  j.test_retry,
  s.hostname AS shard,
  j.require_ssp
FROM
  (
    SELECT *
    FROM afe_jobs
    WHERE id >= %(afe_job_id_start)s
    ORDER BY id ASC
    LIMIT %(limit)s
  ) AS j
  LEFT OUTER JOIN
    afe_shards AS s
    ON j.shard_id = s.id
;
"""

# MySQL query used to retrieve AFE job keyvals.
_AFE_JOB_KEYVALS_QUERY = """
SELECT
  job_id AS afe_job_id,
  `key`,
  value
FROM
  afe_job_keyvals
WHERE
  job_id in %(afe_job_ids)s
;
"""

# MySQL query used to retrieve AFE job dependency labels.
_AFE_JOB_DEPENDENCY_LABELS_QUERY = """
SELECT
  d.job_id AS afe_job_id,
  l.name AS label
FROM
  afe_jobs_dependency_labels AS d
  INNER JOIN
    afe_labels AS l
    ON d.label_id = l.id
WHERE
  job_id in %(afe_job_ids)s
;
"""


class AfeConnection(object):
  """Connection to AFE DB.

  This is a thin wrapper of MySQLWrapper specialized for AFE DB.
  """

  def __init__(self, mysql_wrapper):
    """Initializes the connection.

    Args:
      mysql_wrapper: MySQLWrapper object for AFE DB.
    """
    self._mysql_wrapper = mysql_wrapper

  def QueryJobs(self, afe_job_id_start, limit):
    """Retrieves AFE job rows from the AFE database.

    Rows are returned by the ascending order of the ID.

    Args:
      afe_job_id_start: Minimum AFE job ID.
      limit: Maximum number of rows returned.

    Returns:
      A list of dictionaries representing AFE job rows.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    return self._mysql_wrapper.RunQuery(
        query=_AFE_JOBS_QUERY,
        params={'afe_job_id_start': afe_job_id_start, 'limit': limit},
        description='Dumping AFE jobs')

  def QueryJobKeyvals(self, afe_job_ids):
    """Retrieves AFE job keyval rows from the AFE database.

    Args:
      afe_job_ids: A list of AFE job ids to retrieve keyvals of.

    Returns:
      A list of dictionaries representing AFE job keyval rows.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    return self._mysql_wrapper.RunQuery(
        query=_AFE_JOB_KEYVALS_QUERY,
        params={'afe_job_ids': afe_job_ids},
        description='Dumping AFE job keyvals')

  def QueryJobDependencyLabels(self, afe_job_ids):
    """Retrieves AFE job dependency label rows from the AFE database.

    Args:
      afe_job_ids: A list of AFE job ids to retrieve dependency labels of.

    Returns:
      A list of dictionaries representing AFE job dependency label rows.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    return self._mysql_wrapper.RunQuery(
        query=_AFE_JOB_DEPENDENCY_LABELS_QUERY,
        params={'afe_job_ids': afe_job_ids},
        description='Dumping AFE job dependency labels')
