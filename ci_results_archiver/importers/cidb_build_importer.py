# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Importer implementation for CIDB build database."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime

import pytz

from ci_results_archiver.importers import abstract_importer

# Mapping from CIDB columns to BigQuery columns.
_CIDB_COLUMN_MAP = {
    'id': 'cidb_build_id',
    'master_build_id': 'cidb_master_build_id',
    'builder_name': 'builder_name',
    'buildbot_generation': 'buildbot_generation',
    'waterfall': 'waterfall',
    'build_number': 'build_number',
    'build_config': 'build_config',
    'bot_hostname': 'bot_hostname',
    'start_time': 'start_time',
    'important': 'important',
    'buildbucket_id': 'buildbucket_id',
    'deadline': 'deadline',
    'branch': 'branch',
}


class CidbBuildImporter(abstract_importer.AbstractImporter):
  """Importer implementation for CIDB build database."""

  def __init__(self, cidb, max_entries, grace_period):
    """Initializes the importer.

    Args:
      cidb: CIDBConnection object.
      max_entries: Maximum number of entries to return.
      grace_period: GracePeriod object.
    """
    self._cidb = cidb
    self._max_entries = max_entries
    self._grace_period = grace_period

  def ImportEntries(self, next_id):
    """Imports CIDB build entries."""
    raw_builds = self._cidb.GetBuildsHistory(
        build_configs=None,
        num_results=self._max_entries,
        starting_build_id=next_id,
        reverse=True)

    # Convert schema.
    builds = []
    for raw_build in raw_builds:
      build = _ConvertBuild(raw_build)
      if build:
        builds.append(build)

    builds = self._grace_period.FilterEntries(builds)
    new_next_id = (max(b['cidb_build_id'] for b in builds) + 1
                   if builds else next_id)

    return builds, [], new_next_id


def _ConvertBuild(raw_build):
  """Converts a "raw" build dictionary into a build dictionary.

  A "raw" build dictionary is one returned by cidb.CIDBConnection. This function
  converts it to a dictionary that is expected to be returned from
  CidbBuildImporter.

  Args:
    raw_build: A "raw" build dictionary.

  Returns:
    A build dictionary, or None if the given raw build dictionary is corrupted.
  """
  build = {}
  for old_key, new_key in _CIDB_COLUMN_MAP.iteritems():
    if old_key not in raw_build:
      return None
    value = raw_build[old_key]
    # datetime values returned from CIDBConnection are naive UTC.
    if isinstance(value, datetime.datetime):
      value = pytz.utc.localize(value)
    build[new_key] = value
  return build
