# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Defines the archive table builder."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging


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

  Archive table builder consists of three primary components (importer,
  modifier and exporter):

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
  """

  def __init__(self, importer, modifier, exporter, checkpoint):
    """Constructor.

    Args:
      importer: AbstractImporter object.
      modifier: AbstractModifier object.
      exporter: BigQueryExporter object.
      checkpoint: Checkpoint object.
    """
    self._importer = importer
    self._modifier = modifier
    self._exporter = exporter
    self._checkpoint = checkpoint

  def Run(self):
    """Builds archive tables."""
    # Load the next ID.
    next_id = self._checkpoint.LoadNextId()
    logging.info('Next ID: %d', next_id)

    # Import entries.
    entries, modify_ids = self._importer.ImportEntries(next_id)
    logging.info('Imported %d entries.', len(entries))

    # Modify existing entries if we need to.
    if modify_ids:
      self._modifier.ModifyEntries(modify_ids)

    # Insert new entries. Already existing entries are preserved, so it is
    # safe to repeat multiple times (e.g. when we failed to save new next
    # ID).
    if entries:
      new_next_id = self._exporter.ExportNewEntries(entries)
      logging.info('New next ID: %d', new_next_id)
      self._checkpoint.SaveNextId(new_next_id)

    logging.info('Success: Exported %d entries, updated %d entries.',
                 len(entries), len(modify_ids))
