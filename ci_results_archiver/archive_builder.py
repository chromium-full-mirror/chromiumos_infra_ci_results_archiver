# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Defines the archive table builder."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import time

from chromite.lib import metrics

from ci_results_archiver import constants


class ArchiveBuilder(object):
  r"""Archive table builder.

  About Idempotence
  -----------------

  Builders must be idempotent. That is, even if the script execution is
  aborted in middle of processing (especially during uploads to BigQuery
  tables), next builder run must not miss entries, nor create duplicated
  entries.

  Design Overview
  ---------------

  Archive table builder consists of four primary components (importer,
  modifier, exporter and dumper):

               /------------------------\
               |       MySQL DB         |
               \-----------+------------/
                           |
                           v
                     +-----------+
                     | Importer  |
                     +-----+-----+
                           |
                  +--------+--------+
       modify_ids |                 | new_entries
                  v                 v
            +-----------+      +-----------+
            | Modifier  |      | Exporter  |
            +-----+-----+      +----+------+
                  |                 |
                  v                 v
               /------------------------\
               |       BigQuery         |
               \------------------------/
                           |
                           v
                      +---------+
                      | Dumper  |
                      +----+----+
                           |
                           v
               /------------------------\
               |     Cloud Storage      |
               \------------------------/

  1. Importer: Downloads entries from MySQL databases and returns them as a
     list of dictionaries.

     An entry is identified by unique ID. IDs should be sequentially numbered,
     though skips are allowed.

     For some tables, an importer may also return a list of entry IDs to
     modify which is later passed to a modifier. For example, TkoJobImporter
     returns a list of TKO test IDs to invalidate.

     abstract_importer.AbstractImporter is a class defining the interface of
     importers.

  2. Modifier: Modifies existing entries in BigQuery tables, given a list of
     entry IDs to modify returned from an importer.

     For example, TkoTestModifier receives a list of TKO test IDs to
     invalidate from TkoJobImporter and invalidates those entries in recent
     BigQuery tables.

     abstract_modifier.AbstractModifier is a class defining the interface of
     modifiers. If there is no need to modify existing tables for the target
     table type, a modifier can be None.

  3. BigQueryExporter: Uploads entries to BigQuery tables, given new entries
     from an importer.

     In contrast to importers and modifiers, there is only a single
     implementation of BigQueryExporter and it is shared by all table types.

  4. BigQueryDumper: Dumps BigQuery tables updated by the modifier and the
     exporter to Google Cloud Storage.

     BigQuery tables are dumped as newline-delimited JSON files. They are useful
     for batch access.
  """

  def __init__(self, table_type, importer, modifier, exporter, dumper,
               checkpointer):
    """Constructor.

    Args:
      table_type: TableType object.
      importer: AbstractImporter object.
      modifier: AbstractModifier object.
      exporter: BigQueryExporter object.
      dumper: BigQueryDumper object or None.
      checkpointer: Checkpointer object.
    """
    self._table_type = table_type
    self._importer = importer
    self._modifier = modifier
    self._exporter = exporter
    self._dumper = dumper
    self._checkpointer = checkpointer

  def Run(self):
    """Builds archive tables."""
    metric_prefix = ('%s/builder/%s' % (constants.METRIC_BASE,
                                        self._table_type.value))
    start_time = time.time()

    with metrics.RuntimeBreakdownTimer(metric_prefix) as timer:
      # Load the next ID.
      with timer.Step('load_checkpoint'):
        checkpoint = self._checkpointer.Load()

      next_id = checkpoint.next_id
      logging.info('Next ID: %d', next_id)

      # Import entries.
      with timer.Step('import'):
        entries, modify_ids, new_next_id = self._importer.ImportEntries(next_id)
      logging.info('Imported %d entries.', len(entries))

      updated_table_suffixes = set()

      # Modify existing entries if we need to.
      if modify_ids:
        with timer.Step('modify'):
          modified_table_suffixes = self._modifier.ModifyEntries(modify_ids)
          updated_table_suffixes.update(modified_table_suffixes)

      # Insert new entries. Already existing entries are preserved, so it is
      # safe to repeat multiple times (e.g. when we failed to save new next
      # ID).
      if entries:
        with timer.Step('export'):
          exported_table_suffixes = self._exporter.ExportNewEntries(entries)
          updated_table_suffixes.update(exported_table_suffixes)

      # Dump updated tables.
      if updated_table_suffixes and self._dumper:
        with timer.Step('dump'):
          self._dumper.DumpTables(list(updated_table_suffixes))

      logging.info('New next ID: %d', new_next_id)
      new_checkpoint = checkpoint._replace(
          next_id=new_next_id, last_start_time=start_time)

      with timer.Step('save_checkpoint'):
        self._checkpointer.Save(new_checkpoint)

    logging.info('Success: Exported %d entries, updated %d entries.',
                 len(entries), len(modify_ids))

    metrics.GaugeMetric('%s/next_id' % metric_prefix).set(next_id)
    metrics.CounterMetric(
        '%s/modify_count' % metric_prefix).increment_by(len(modify_ids))
    metrics.CounterMetric(
        '%s/export_count' % metric_prefix).increment_by(len(entries))
