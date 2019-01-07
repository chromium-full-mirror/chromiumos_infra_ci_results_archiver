# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Fake implementation of AfeConnection."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class FakeAfeConnection(object):
  """Fake implementation of AfeConnection.

  Attributes:
    jobs: List of job dictionaries.
    job_keyvals: List of job keyval dictionaries.
    job_dependency_labels: List of job dependency label dictionaries.
    special_tasks: List of special task dictionaries.
    host_attributes: List of host attribute dictionaries.
    host_labels: List of host label dictionaries.
  """

  def __init__(self,
               jobs=None,
               job_keyvals=None,
               job_dependency_labels=None,
               special_tasks=None,
               host_attributes=None,
               host_labels=None):
    """Constructor."""
    self.jobs = jobs or []
    self.job_keyvals = job_keyvals or []
    self.job_dependency_labels = job_dependency_labels or []
    self.special_tasks = special_tasks or []
    self.host_attributes = host_attributes or []
    self.host_labels = host_labels or []

  def QueryJobs(self, afe_job_id_start, limit):
    """Retrieves AFE job rows from the local database."""
    jobs = [job for job in self.jobs if job['afe_job_id'] >= afe_job_id_start]
    jobs.sort(key=lambda job: job['afe_job_id'])
    return jobs[:limit]

  def QueryJobKeyvals(self, afe_job_ids):
    """Retrieves AFE job keyval rows from the local database."""
    job_keyvals = [
        job_keyval for job_keyval in self.job_keyvals
        if job_keyval['afe_job_id'] in afe_job_ids
    ]
    return job_keyvals

  def QueryJobDependencyLabels(self, afe_job_ids):
    """Retrieves AFE job dependency label rows from the local database."""
    job_dependency_labels = [
        job_dependency_label
        for job_dependency_label in self.job_dependency_labels
        if job_dependency_label['afe_job_id'] in afe_job_ids
    ]
    return job_dependency_labels

  def QuerySpecialTasks(self, afe_special_task_id_start, limit):
    """Retrieve AFE special agent task rows from the local database."""
    special_tasks = [
        special_task for special_task in self.special_tasks
        if special_task['afe_special_task_id'] >= afe_special_task_id_start
    ]
    special_tasks.sort(
        key=lambda special_task: special_task['afe_special_task_id'])
    return special_tasks[:limit]

  def QueryHostAttributes(self, afe_host_ids):
    """Retrieve AFE host attribute rows from the local database."""
    host_attributes = [
        host_attribute for host_attribute in self.host_attributes
        if host_attribute['host_id'] in afe_host_ids
    ]
    return host_attributes

  def QueryHostLabels(self, afe_host_ids):
    """Retrieve AFE host label rows from the local database."""
    host_labels = [
        host_label for host_label in self.host_labels
        if host_label['host_id'] in afe_host_ids
    ]
    return host_labels
