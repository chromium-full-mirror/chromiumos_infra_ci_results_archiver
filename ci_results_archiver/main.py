# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""BigQuery table builder.

This program runs in one of following two modes depending on command line
arguments:

1. One-shot mode (if --one-shot option is given). The program runs a builder
   for tables of the type specified by --table-type and exits. This mode is
   usually invoked by a daemon described next, but is also useful for debugging.

2. Daemon mode (if --one-shot option is NOT given). The program starts as
   a daemon process running forever. It periodically executes itself in one-shot
   mode as subprocesses.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import datetime
import logging
import multiprocessing
import signal
import sys

from apscheduler.executors import pool as pool_executors
from apscheduler.schedulers import blocking as blocking_scheduler
from apscheduler.triggers import interval as interval_triggers
import subprocess32

from ci_results_archiver import archive_builder_factory
from ci_results_archiver import config_loader
from ci_results_archiver import table_types
from ci_results_archiver.utils import text_util

import pytz


def _DaemonMain(run_soon, configs):
  """The entry point for a daemon process.

  Args:
    run_soon: If True, start builders soon.
    configs: Configuration dictionary.
  """
  # We do not use ProcessPoolExecutor because its underlying multiprocessing
  # module easily deadlocks on signals.
  executor = pool_executors.ThreadPoolExecutor(
      max_workers=len(table_types.TableType))
  scheduler = blocking_scheduler.BlockingScheduler(
      executors={'default': executor})
  if run_soon:
    # Start jobs in 3 seconds.
    start_date = datetime.datetime.now() + datetime.timedelta(seconds=3)
  else:
    # Set the start date UNIX epoch so that jobs start in consistent periods.
    start_date = datetime.datetime.fromtimestamp(0, pytz.utc)
  interval = text_util.ParseTimeDelta(configs['scheduler']['interval'])
  trigger = interval_triggers.IntervalTrigger(
      seconds=interval.total_seconds(), start_date=start_date)

  timeout = text_util.ParseTimeDelta(configs['scheduler']['timeout'])

  for table_type in table_types.TableType:
    scheduler.add_job(
        name=table_type.value,
        func=_RunBuilder,
        kwargs={'table_type': table_type, 'timeout': timeout},
        trigger=trigger,
        max_instances=1)

  try:
    scheduler.start()
  except KeyboardInterrupt:
    logging.info('Received a signal. Exiting.')


def _RunBuilder(table_type, timeout):
  """Spawns a subprocess to run a builder for the specified tables.

  Args:
    table_type: TableType value.
    timeout: Timeout in datetime.timedelta.

  Raises:
    subprocess.CalledProcessError: When a subprocess exited with errors.
  """
  builder_argv = (
      [sys.executable] + sys.argv +
      ['--one-shot', '--table-type=%s' % table_type.value])
  subprocess32.check_call(builder_argv, timeout=timeout.total_seconds())


def _BuilderMain(table_type, configs):
  """The entry point for builder processes.

  Args:
    table_type: TableType to build tables of.
    configs: Configuration dictionary.
  """
  builder = archive_builder_factory.CreateBuilder(
      table_type=table_type, configs=configs)
  builder.Run()


def _SetupLogging(verbose, process_name):
  """Sets up logging.

  Args:
    verbose: If True, turns on verbose debug logging.
    process_name: Process name to show in log lines.
  """
  multiprocessing.current_process().name = process_name
  logging.basicConfig(
      level=(logging.DEBUG if verbose else logging.INFO),
      format=('%(levelname)s %(asctime)-15s %(processName)s '
              '[%(filename)s:%(lineno)d] %(message)s'),
      datefmt='%Y-%m-%d %H:%M:%S')


def _ParseArgs():
  """Parses command line arguments.

  Returns:
    argparse.ArgumentParser object.
  """
  parser = argparse.ArgumentParser(
      prog='ci_results_archiver',
      description=__doc__,
      formatter_class=argparse.RawDescriptionHelpFormatter)

  parser.add_argument(
      '-v', '--verbose', action='store_true', help='Enable verbose logging.')
  parser.add_argument(
      '-c',
      '--config',
      dest='config_path',
      metavar='PATH',
      required=True,
      help='Path to a config file.')
  parser.add_argument(
      '--run-soon',
      action='store_true',
      help='Runs jobs soon after the start of the script.')
  parser.add_argument(
      '--one-shot', action='store_true', help='Runs in one-shot mode.')
  parser.add_argument(
      '--table-type',
      type=table_types.TableType,
      metavar='TYPE',
      help='If this option is set, the program builds tables of the specified '
      'type and exits.')
  options = parser.parse_args()

  if options.one_shot:
    if not options.table_type:
      logging.error('--table-type must be set in one-shot mode')
      sys.exit(1)
  else:
    if options.table_type:
      logging.error('--table-type must not be set in daemon mode')
      sys.exit(1)

  return options


def main():
  """The entry point."""
  # Install SIGTERM handler so we can clean up.
  signal.signal(signal.SIGTERM, signal.default_int_handler)

  options = _ParseArgs()
  configs = config_loader.Load(options.config_path)

  process_name = options.table_type.value if options.table_type else 'scheduler'
  _SetupLogging(verbose=options.verbose, process_name=process_name)

  if options.table_type:
    _BuilderMain(table_type=options.table_type, configs=configs)
  else:
    _DaemonMain(run_soon=options.run_soon, configs=configs)


if __name__ == '__main__':
  main()
