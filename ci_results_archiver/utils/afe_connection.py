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

# MySQL query used to retrieve AFE special tasks.
_AFE_SPECIAL_TASKS_QUERY = """
SELECT
  t.id AS afe_special_task_id,
  t.host_id,
  h.hostname,
  h.status,
  t.task,
  t.is_active,
  t.is_complete,
  t.time_started,
  t.time_finished,
  t.success
FROM afe_special_tasks AS t
  INNER JOIN afe_hosts AS h ON h.id = t.host_id
WHERE t.id >= %(afe_special_task_id_start)s
  AND h.invalid = 0
ORDER BY t.id ASC
LIMIT %(limit)s
;
"""

# MySQL query used to retrieve AFE host labels.
_AFE_HOSTS_LABELS_QUERY = """
SELECT
  hosts_labels.host_id,
  label.name
FROM afe_hosts_labels AS hosts_labels
  INNER JOIN afe_labels AS label ON label.id = hosts_labels.label_id
WHERE hosts_labels.host_id IN %(afe_host_ids)s
;
"""

# MySQL query used to retrieve AFE host attributes.
_AFE_HOST_ATTRIBUTES_QUERY = """
SELECT
  host_id,
  attribute,
  value
FROM afe_host_attributes
WHERE host_id IN %(afe_host_ids)s
  AND attribute IN ('HWID', 'serial_number', 'servo_host', 'servo_port')
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

  def QuerySpecialTasks(self, afe_special_task_id_start, limit):
    """Retrieves AFE special tasks from the AFE database.

    Rows are returned by the ascending order of the ID.

    Args:
      afe_special_task_id_start: Minimum AFE special task ID.
      limit: Maximum number of rows returned.

    Returns:
      A list of dictionaries representing AFE special task rows.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    return self._mysql_wrapper.RunQuery(
        query=_AFE_SPECIAL_TASKS_QUERY,
        params={
            'afe_special_task_id_start': afe_special_task_id_start,
            'limit': limit
        },
        description='Dumping AFE special tasks')

  def QueryHostAttributes(self, afe_host_ids):
    """Retrieves AFE host attribute rows from the AFE database.

    Only the following attributes are returned for a host: HWID, serial_number,
    servo_host, servo_port.

    Args:
      afe_host_ids: A list AFE host ids to retrieve host attributes of.

    Returns:
      A list of dictionaries representing AFE host attribute rows.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    return self._mysql_wrapper.RunQuery(
        query=_AFE_HOST_ATTRIBUTES_QUERY,
        params={'afe_host_ids': afe_host_ids},
        description='Dumping AFE host attributes')

  def QueryHostLabels(self, afe_host_ids):
    """Retrieves AFE host label rows from the AFE database.

    Args:
      afe_host_ids: A list of AFE host ids to retrieve host labels of.

    Returns:
      A list of dictionaries representing AFE host label rows.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    return self._mysql_wrapper.RunQuery(
        query=_AFE_HOSTS_LABELS_QUERY,
        params={'afe_host_ids': afe_host_ids},
        description='Dumping AFE host labels')
