# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for cidb_build_importer."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import unittest

from chromite.lib import cidb
from chromite.lib import fake_cidb
import mock
import pytz

from ci_results_archiver.importers import cidb_build_importer
from ci_results_archiver.importers import grace_period

DEFAULT_GRACE_PERIOD = grace_period.GracePeriod(
    id_column='cidb_build_id',
    insertion_timestamp_column='start_time',
    timeout=None,
    capacity=0)


class CidbBuildImporterTestCase(unittest.TestCase):
  """Unit tests for CidbBuildImporter."""

  def setUp(self):
    """Setup."""
    self._cidb = fake_cidb.FakeCIDBConnection()

  def testNormal(self):
    """ImportEntries() works in a usual case."""
    self._cidb.InsertBuild(**_CreateCidbBuildEntry())
    self._cidb.InsertBuild(**_CreateCidbBuildEntry())

    importer = cidb_build_importer.CidbBuildImporter(
        cidb=self._cidb, max_entries=10, grace_period=DEFAULT_GRACE_PERIOD)
    entries, modify_ids, new_next_id = importer.ImportEntries(next_id=0)

    self.assertEquals([
        {
            'cidb_build_id': 0,
            'cidb_master_build_id': 123,
            'builder_name': 'link-paladin',
            'buildbot_generation': 1,
            'waterfall': 'chromiumos',
            'build_number': 345,
            'build_config': 'link-paladin-config',
            'bot_hostname': 'somehost',
            'start_time': datetime.datetime.fromtimestamp(1234567890, pytz.utc),
            'important': True,
            'buildbucket_id': 'someid',
            'deadline': datetime.datetime.fromtimestamp(1234567900, pytz.utc),
            'branch': 'master',
        },
        {
            'cidb_build_id': 1,
            'cidb_master_build_id': 123,
            'builder_name': 'link-paladin',
            'buildbot_generation': 1,
            'waterfall': 'chromiumos',
            'build_number': 345,
            'build_config': 'link-paladin-config',
            'bot_hostname': 'somehost',
            'start_time': datetime.datetime.fromtimestamp(1234567890, pytz.utc),
            'important': True,
            'buildbucket_id': 'someid',
            'deadline': datetime.datetime.fromtimestamp(1234567900, pytz.utc),
            'branch': 'master',
        },
    ], entries)
    self.assertEquals([], modify_ids)
    self.assertEquals(2, new_next_id)

  def testImportRange(self):
    """ImportEntries() handles next_id and max_entries."""
    self._cidb.InsertBuild(**_CreateCidbBuildEntry())
    self._cidb.InsertBuild(**_CreateCidbBuildEntry())
    self._cidb.InsertBuild(**_CreateCidbBuildEntry())
    self._cidb.InsertBuild(**_CreateCidbBuildEntry())
    self._cidb.InsertBuild(**_CreateCidbBuildEntry())
    self._cidb.InsertBuild(**_CreateCidbBuildEntry())

    importer = cidb_build_importer.CidbBuildImporter(
        cidb=self._cidb, max_entries=2, grace_period=DEFAULT_GRACE_PERIOD)
    entries, _, new_next_id = importer.ImportEntries(next_id=3)

    self.assertEquals(2, len(entries))
    self.assertEquals(3, entries[0]['cidb_build_id'])
    self.assertEquals(4, entries[1]['cidb_build_id'])
    self.assertEquals(5, new_next_id)

  def testNoEntries(self):
    """ImportEntries() works even if there is no entry to import."""
    importer = cidb_build_importer.CidbBuildImporter(
        cidb=self._cidb, max_entries=10, grace_period=DEFAULT_GRACE_PERIOD)
    entries, _, new_next_id = importer.ImportEntries(next_id=123)

    self.assertEquals(0, len(entries))
    self.assertEquals(123, new_next_id)

  def testCorruptedBuild(self):
    """ImportEntries() handles corrupted builds from CIDBConnection."""
    mock_cidb = mock.create_autospec(cidb.CIDBConnection)
    mock_cidb.GetBuildsHistory.return_value = [{}]

    importer = cidb_build_importer.CidbBuildImporter(
        cidb=mock_cidb, max_entries=10, grace_period=DEFAULT_GRACE_PERIOD)
    entries, _, new_next_id = importer.ImportEntries(next_id=123)

    self.assertEquals(0, len(entries))
    self.assertEquals(123, new_next_id)


def _CreateCidbBuildEntry(
    master_build_id=123,
    builder_name='link-paladin',
    waterfall='chromiumos',
    build_number=345,
    build_config='link-paladin-config',
    bot_hostname='somehost',
    start_time=datetime.datetime.utcfromtimestamp(1234567890),
    important=True,
    buildbucket_id='someid',
    timeout_seconds=10,
    branch='master'):
  """Creates args for FakeCIDBConnection.InsertBuild()."""
  # pylint: disable=unused-argument
  return dict(locals())
