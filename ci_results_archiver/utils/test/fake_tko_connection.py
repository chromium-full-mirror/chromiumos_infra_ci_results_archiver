# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Fake implementation of TkoConnection."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class FakeTkoConnection(object):
  """Fake implementation of TkoConnection.

  Attributes:
    jobs: List of job dictionaries.
    job_keyvals: List of job keyval dictionaries.
    tests: List of test dictionaries.
  """

  def __init__(self, jobs=None, job_keyvals=None, tests=None):
    """Constructor.

    Attributes:
      jobs: List of job dictionaries.
      job_keyvals: List of job keyval dictionaries.
      tests: List of test dictionaries.
    """
    self.jobs = jobs or []
    self.job_keyvals = job_keyvals or []
    self.tests = tests or []

  def QueryLargestJobId(self):
    """Retrieves the largest TKO job ID from the TKO database."""
    return max(job['tko_job_id'] for job in self.jobs)

  def QueryJobs(self, tko_job_id_start, limit):
    """Retrieves TKO job rows from the local database."""
    jobs = [job for job in self.jobs if job['tko_job_id'] >= tko_job_id_start]
    jobs.sort(key=lambda job: job['tko_job_id'])
    return jobs[:limit]

  def QueryJobKeyvals(self, tko_job_ids):
    """Retrieves TKO job keyval rows from the local database."""
    job_keyvals = [
        job_keyval for job_keyval in self.job_keyvals
        if job_keyval['tko_job_id'] in tko_job_ids
    ]
    return job_keyvals

  def QueryTests(self, tko_job_ids):
    """Retrieves TKO test rows from the local database."""
    tests = [test for test in self.tests if test['tko_job_id'] in tko_job_ids]
    return tests
