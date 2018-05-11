# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Set tko_jobs.afe_parent_job_id to NULL instead of 0.

For crbug.com/841688
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import logging

from ci_results_archiver.contrib.oneoff import common

_SET_AFE_PARENT_JOB_ID = """
UPDATE `%s`
SET afe_parent_job_id = NULL
WHERE afe_parent_job_id = 0
;
"""


def _FixupTable(bq_wrapper, table_name):
  """Callback for TableUpdater to fix a single table."""
  bq_wrapper.RunQuery(
      _SET_AFE_PARENT_JOB_ID % table_name,
      timeout_seconds=300,
      description='Setting 0 afe_parent_job_ids to NULL')


def main():
  """main function."""
  logging.basicConfig(level=logging.INFO)
  parser = argparse.ArgumentParser(
      description='Replace tko_jobs.afe_parent_job_id 0 vaules with NULL')
  common.ParserAddOneoffArgs(parser)
  options = parser.parse_args()

  table_updater = common.TableUpdater(options)
  table_updater.Execute(_FixupTable)


if __name__ == '__main__':
  main()
