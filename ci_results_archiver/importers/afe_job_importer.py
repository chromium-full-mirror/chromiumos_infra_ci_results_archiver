# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Importer implementation for afe_jobs database."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from ci_results_archiver.importers import abstract_importer

# Job enum value-to-name mappings.
_JOB_ENUM_MAPPINGS = {
    'control_type': {
        1: 'SERVER',
        2: 'CLIENT',
    },
    'reboot_before': {
        0: 'NEVER',
        1: 'IF_DIRTY',
        2: 'ALWAYS',
    },
    'reboot_after': {
        0: 'NEVER',
        1: 'IF_ALL_TESTS_PASSED',
        2: 'ALWAYS',
    },
}


class AfeJobImporter(abstract_importer.AbstractImporter):
  """Importer implementation for afe_jobs database."""

  def __init__(self, afe, max_entries, grace_period):
    """Initializes the importer.

    Args:
      afe: AfeConnection object.
      max_entries: Maximum number of entries to return.
      grace_period: GracePeriod object.
    """
    self._afe = afe
    self._max_entries = max_entries
    self._grace_period = grace_period

  def ImportEntries(self, next_id):
    """Imports AFE job entries."""
    job_map = self._QueryJobMap(next_id)
    if not job_map:
      return [], [], next_id

    job_keyvals_map = self._QueryJobKeyvalsMap(job_map.keys())
    job_dependency_labels_map = self._QueryJobDependencyLabelsMap(
        job_map.keys())

    # Join to jobs.
    for job_id, job in job_map.iteritems():
      job['keyvals'] = job_keyvals_map[job_id]
      job['dependency_labels'] = job_dependency_labels_map[job_id]

    jobs = job_map.values()
    new_next_id = max(j['afe_job_id'] for j in jobs) + 1 if jobs else next_id

    return jobs, [], new_next_id

  def _QueryJobMap(self, next_id):
    """Retrieves AFE job entries from the AFE database.

    Args:
      next_id: ID to start importing.

    Returns:
      A dictionary whose key is a job ID and value is a job dictionary.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    jobs = self._afe.QueryJobs(
        afe_job_id_start=next_id, limit=self._max_entries)

    jobs = self._grace_period.FilterEntries(jobs)

    for job in jobs:
      # Truncate too long control files.
      job['control_file'] = job['control_file'][:8192]
      for key, mapping in _JOB_ENUM_MAPPINGS.iteritems():
        job[key] = mapping[job[key]]

    return {job['afe_job_id']: job for job in jobs}

  def _QueryJobKeyvalsMap(self, job_ids):
    """Retrieves AFE job keyvals from the AFE database.

    Args:
      job_ids: A list of AFE job IDs to retrieve keyvals of.

    Returns:
      A dictionary whose key is a job ID and value is a list of keyvals.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    all_keyvals = self._afe.QueryJobKeyvals(afe_job_ids=job_ids)

    job_keyvals_map = {job_id: [] for job_id in job_ids}
    for keyval in all_keyvals:
      job_id = keyval.pop('afe_job_id')
      job_keyvals_map[job_id].append(keyval)

    for keyvals in job_keyvals_map.itervalues():
      keyvals.sort(key=lambda keyval: keyval['key'])

    return job_keyvals_map

  def _QueryJobDependencyLabelsMap(self, job_ids):
    """Retrieves AFE job dependency labels from the AFE database.

    Args:
      job_ids: A list of AFE job IDs to retrieve dependency labels of.

    Returns:
      A dictionary whose key is a job ID and value is a list of dependency
         labels.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    all_dependency_labels = self._afe.QueryJobDependencyLabels(
        afe_job_ids=job_ids)

    job_dependency_labels_map = {job_id: [] for job_id in job_ids}
    for label in all_dependency_labels:
      job_id = label['afe_job_id']
      job_dependency_labels_map[job_id].append(label['label'])

    for dependency_labels in job_dependency_labels_map.itervalues():
      dependency_labels.sort()

    return job_dependency_labels_map
