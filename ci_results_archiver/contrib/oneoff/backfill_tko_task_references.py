# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Backfill tko_jobs.{task_reference_type,task_id,parent_task_id}.

For b/78659566
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import logging

from ci_results_archiver import table_specs
from ci_results_archiver.contrib.oneoff import common

_SET_AFE_PARENT_JOB_ID = """
UPDATE `%s`
SET task_reference_type = 'afe',
    task_id = CAST(afe_job_id AS STRING),
    parent_task_id = CAST(afe_parent_job_id AS STRING)
WHERE true
;
"""

_NEW_COLUMNS = {'task_reference_type', 'task_id', 'parent_task_id'}


def _FixupTable(bq_wrapper, table_name):
  """Callback for TableUpdater to fix a single table."""
  schema = bq_wrapper.TableSchema(table_name)
  column_names = {s.name for s in schema}
  if _NEW_COLUMNS - column_names:
    logging.info('Updating table schema for %s', table_name)
    bq_wrapper.PatchSchema(table_name, schema=table_specs.TKO_JOBS.schema)
  bq_wrapper.RunQuery(
      _SET_AFE_PARENT_JOB_ID % table_name,
      timeout_seconds=300,
      description='Backfilling tko_task_references')


def main():
  """main function."""
  logging.basicConfig(level=logging.INFO)
  parser = argparse.ArgumentParser(description='Backfill tko_task_references')
  common.ParserAddOneoffArgs(parser)
  options = parser.parse_args()

  table_updater = common.TableUpdater(options)
  table_updater.Execute(_FixupTable)


if __name__ == '__main__':
  main()
