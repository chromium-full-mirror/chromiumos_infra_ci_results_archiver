# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Importer implementation for tko_jobs/tko_tests database."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from ci_results_archiver.importers import abstract_importer


class TkoJobImporter(abstract_importer.AbstractImporter):
  """Importer implementation for tko_jobs/tko_tests database."""

  def __init__(self, tko, max_entries, grace_period):
    """Initializes the importer.

    Args:
      tko: TkoConnection object.
      max_entries: Maximum number of entries to return.
      grace_period: GracePeriod object.
    """
    self._tko = tko
    self._max_entries = max_entries
    self._grace_period = grace_period

  def ImportEntries(self, next_id):
    """Imports TKO job entries."""
    job_map = self._QueryJobMap(next_id)
    if not job_map:
      return [], [], next_id

    self._SetTaskReferences(job_map)
    job_keyvals_map = self._QueryJobKeyvalsMap(job_map.keys())
    tests_map = self._QueryTestsMap(job_map.keys())

    # Join to jobs.
    for job_id, job in job_map.iteritems():
      job['keyvals'] = job_keyvals_map[job_id]
      job['tests'] = tests_map[job_id]

    jobs = job_map.values()
    invalid_tko_test_ids = self._ScanAndApplyInvalidation(jobs)
    new_next_id = max(j['tko_job_id'] for j in jobs) + 1 if jobs else next_id
    return jobs, invalid_tko_test_ids, new_next_id

  def _QueryJobMap(self, next_id):
    """Retrieves TKO job entries from the TKO database.

    Args:
      next_id: ID to start importing.

    Returns:
      A dictionary whose key is a job ID and value is a job dictionary.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    jobs = self._tko.QueryJobs(
        tko_job_id_start=next_id, limit=self._max_entries)

    jobs = self._grace_period.FilterEntries(jobs)

    return {job['tko_job_id']: job for job in jobs}

  def _SetTaskReferences(self, job_map):
    """Retrieves TKO task references from the TKO database and updates job_map.

    Args:
      job_map: A dictionary whose key is a job ID and value is a job dictionary.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    task_references = self._tko.QueryTaskReferences(job_map.keys())
    for task_reference in task_references:
      job_id = task_reference['tko_job_id']
      job = job_map[job_id]
      job['task_reference_type'] = task_reference['reference_type']
      job['task_id'] = task_reference['task_id']
      job['parent_task_id'] = task_reference['parent_task_id']

  def _QueryJobKeyvalsMap(self, job_ids):
    """Retrieves TKO job keyvals from the TKO database.

    Args:
      job_ids: A list of TKO job IDs to retrieve keyvals of.

    Returns:
      A dictionary whose key is a job ID and value is a list of keyvals.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    all_keyvals = self._tko.QueryJobKeyvals(tko_job_ids=job_ids)

    job_keyvals_map = {job_id: [] for job_id in job_ids}
    for keyval in all_keyvals:
      job_id = keyval.pop('tko_job_id')
      job_keyvals_map[job_id].append(keyval)

    for keyvals in job_keyvals_map.itervalues():
      keyvals.sort(key=lambda keyval: keyval['key'])

    return job_keyvals_map

  def _QueryTestsMap(self, job_ids):
    """Retrieves TKO tests from the TKO database.

    Args:
      job_ids: A list of TKO job IDs to retrieve tests of.

    Returns:
      A dictionary whose key is a job ID and value is a list of tests.

    Raises:
      MySQLdb.Error: On MySQL errors.
    """
    all_tests = self._tko.QueryTests(tko_job_ids=job_ids)

    tests_map = {job_id: [] for job_id in job_ids}
    for test in all_tests:
      job_id = test.pop('tko_job_id')
      tests_map[job_id].append(test)

    for tests in tests_map.itervalues():
      tests.sort(key=lambda t: t['tko_test_id'])

    return tests_map

  def _ScanAndApplyInvalidation(self, jobs):
    """Scans test entries and applies invalidation.

    Rows in TKO tko_tests table can be invalidated when a test result
    is overridden by a retry run (see tko/parse.py). In this case,
    `invalid` column of an overridden test is set to true, and also
    `invalidates_test_idx` column of an overriding test is set to the
    ID of an overridden test.

    This function scans |jobs| and invalidates tests referenced in
    `invalidates_test_idx`. If a test referenced in the column is not
    found in |jobs|, it means we already processed it in an earlier run,
    possibly leaving it as "not invalid". In this case we need to
    update existing rows in BigQuery tables to invalidate such entries.

    Args:
      jobs: A list of dictionaries representing TKO jobs.

    Returns:
      A list of TKO test IDs to be invalidated, or None.
    """
    all_tests = []
    for job in jobs:
      all_tests.extend(job['tests'])

    invalid_test_id_set = set()
    for test in all_tests:
      invalid_test_id = test['invalidating_tko_test_id']
      if invalid_test_id:
        invalid_test_id_set.add(invalid_test_id)

    # Apply invalidations in the current test set.
    for test in all_tests:
      if test['tko_test_id'] in invalid_test_id_set:
        test['invalid'] = 1
        invalid_test_id_set.discard(test['tko_test_id'])

    # Some tests were processed in last iteration so we need to update them.
    return sorted(invalid_test_id_set)
