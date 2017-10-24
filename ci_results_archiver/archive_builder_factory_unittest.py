# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for archive_builder_factory."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import unittest

import mock
import pytz

from ci_results_archiver import archive_builder
from ci_results_archiver import archive_builder_factory
from ci_results_archiver import bigquery_dumper
from ci_results_archiver import bigquery_exporter
from ci_results_archiver import checkpointer
from ci_results_archiver import config_loader
from ci_results_archiver import table_types
from ci_results_archiver.importers import afe_job_importer
from ci_results_archiver.importers import cidb_build_importer
from ci_results_archiver.importers import tko_job_importer
from ci_results_archiver.modifiers import tko_job_test_invalidator

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), 'test/config_example.yaml')


class ArchiveBuilderFactoryTestCase(unittest.TestCase):
  """Unit tests for archive_builder_factory."""

  def setUp(self):
    """Setup."""
    self.mysql_mock = self._Patch(
        'ci_results_archiver.utils.mysql_wrapper.MySQLWrapper')
    self.cidb_mock = self._Patch('chromite.lib.cidb.CIDBConnection')
    self.bigquery_mock = self._Patch('google.cloud.bigquery.Client')
    self.storage_mock = self._Patch('google.cloud.storage.Client')

  def testAfeJobs(self):
    """CreateBuilder() for afe_jobs."""
    # pylint: disable=protected-access
    configs = config_loader.Load(_CONFIG_PATH)
    builder = archive_builder_factory.CreateBuilder(
        table_types.TableType.AFE_JOBS, configs)

    self.assertIsInstance(builder, archive_builder.ArchiveBuilder)

    self.assertIsInstance(builder._importer, afe_job_importer.AfeJobImporter)
    self.assertIs(builder._modifier, None)
    self.assertIsInstance(builder._dumper, bigquery_dumper.BigQueryDumper)
    self.assertIsInstance(builder._exporter, bigquery_exporter.BigQueryExporter)
    self.assertIsInstance(builder._checkpointer, checkpointer.Checkpointer)

    self.mysql_mock.assert_called_once_with(
        hostname='afehostname',
        username='afeusername',
        password='afepassword',
        database='afedatabase',
        timezone=pytz.timezone('US/Pacific'))
    self.cidb_mock.assert_not_called()
    self.bigquery_mock.assert_called_once_with('bqproject')
    self.bigquery_mock.return_value.dataset.assert_called_once_with(
        'somedataset')
    self.storage_mock.assert_called_once_with('gcsproject')
    self.storage_mock.return_value.bucket.assert_has_calls(
        [
            mock.call('somebucket'),
            mock.call('goodbucket'),
        ], any_order=True)

  def testTkoJobs(self):
    """CreateBuilder() for tko_jobs."""
    # pylint: disable=protected-access
    configs = config_loader.Load(_CONFIG_PATH)
    builder = archive_builder_factory.CreateBuilder(
        table_types.TableType.TKO_JOBS, configs)

    self.assertIsInstance(builder, archive_builder.ArchiveBuilder)

    self.assertIsInstance(builder._importer, tko_job_importer.TkoJobImporter)
    self.assertIsInstance(builder._modifier,
                          tko_job_test_invalidator.TkoJobTestInvalidator)
    self.assertIsInstance(builder._dumper, bigquery_dumper.BigQueryDumper)
    self.assertIsInstance(builder._exporter, bigquery_exporter.BigQueryExporter)
    self.assertIsInstance(builder._checkpointer, checkpointer.Checkpointer)

    self.mysql_mock.assert_called_once_with(
        hostname='tkohostname',
        username='tkousername',
        password='tkopassword',
        database='tkodatabase',
        timezone=pytz.timezone('Asia/Tokyo'))
    self.cidb_mock.assert_not_called()
    self.bigquery_mock.assert_called_once_with('bqproject')
    self.bigquery_mock.return_value.dataset.assert_called_once_with(
        'somedataset')
    self.storage_mock.assert_called_once_with('gcsproject')
    self.storage_mock.return_value.bucket.assert_has_calls(
        [
            mock.call('somebucket'),
            mock.call('goodbucket'),
        ], any_order=True)

  def testCidbBuilds(self):
    """CreateBuilder() for cidb_builds."""
    # pylint: disable=protected-access
    configs = config_loader.Load(_CONFIG_PATH)
    builder = archive_builder_factory.CreateBuilder(
        table_types.TableType.CIDB_BUILDS, configs)

    self.assertIsInstance(builder, archive_builder.ArchiveBuilder)

    self.assertIsInstance(builder._importer,
                          cidb_build_importer.CidbBuildImporter)
    self.assertIs(builder._modifier, None)
    self.assertIs(builder._dumper, None)
    self.assertIsInstance(builder._exporter, bigquery_exporter.BigQueryExporter)
    self.assertIsInstance(builder._checkpointer, checkpointer.Checkpointer)

    self.mysql_mock.assert_not_called()
    self.cidb_mock.assert_called_once_with('/path/to/cidb_creds')
    self.bigquery_mock.assert_called_once_with('bqproject')
    self.bigquery_mock.return_value.dataset.assert_called_once_with(
        'somedataset')
    self.storage_mock.assert_called_once_with('gcsproject')
    self.storage_mock.return_value.bucket.assert_has_calls(
        [
            mock.call('somebucket'),
            mock.call('goodbucket'),
        ], any_order=True)

  def _Patch(self, name):
    """Mocks out an object using mock.patch(), and restores it after the test.

    Args:
      name: Fully-qualified object name to be patched.

    Returns:
      mock.Mock object.
    """
    patcher = mock.patch(name, autospec=True)
    mock_obj = patcher.start()
    self.addCleanup(patcher.stop)
    return mock_obj
