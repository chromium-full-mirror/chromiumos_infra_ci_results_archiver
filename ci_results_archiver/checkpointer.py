# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Manages "next ID" to process."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import json

from google.cloud import exceptions  # pylint: disable=import-error,no-name-in-module
from google.cloud import datastore

class Checkpointer(object):
  """Manages checkpoints.

  A checkpoint is an entity in Google Cloud Datastore containing various
  information persisted between builder runs.

  The most important information in a checkpoint is "Next ID" which identifies
  the primary ID of the oldest unprocessed entry in the source database.
  On a successful run of the BigQuery table builder pipeline,
  (maximum ID of entries processed in a run) + 1 will be saved as a next ID,
  and on a next run it is read to continue processing subsequent entries.
  """

  def __init__(self, project, kind, entity):
    """Initializes the checkpointer object. """

    self.client = datastore.Client(project)
    self.kind = kind
    self.entity = entity


  def Load(self):
    """Loads a checkpoint.

    Returns:
      Checkpoint object.

    Raises:
      CheckpointError: When the checkpoint is corrupted or not found.
    """

    key = self.client.key(self.kind, self.entity)
    content = self.client.get(key)
    if not content:
      raise CheckpointError(
          'Checkpoint entity is empty. If this is the first run, '
          'please create one under kind %s with name '
          '%s manually in Google Cloud Console.' %
          (self.kind, self.entity))
    checkpoint = Checkpoint(
        next_id=int(content.get('next_id')),
        last_start_time=float(content.get('last_start_time')))
    if not checkpoint.next_id:
      raise CheckpointError('Checkpoint entity is corrupted: next_id is not set.')
    return checkpoint

  def Save(self, checkpoint):
    """Saves a checkpoint.

    Args:
      checkpoint: Checkpoint object to be saved as an entity in datastore.

    Raises:
      CheckpointError: When the checkpoint is not found.
    """
    with self.client.transaction():
      key = self.client.key(self.kind, self.entity)
      content = self.client.get(key)
      if not content:
        raise CheckpointError(
          'Checkpoint entity is empty. If this is the first run, '
          'please create one under kind %s with name '
          '%s manually in Google Cloud Console.' %
          (self.kind, self.entity))
      content['next_id'] = str(checkpoint.next_id)
      content['last_start_time'] = str(checkpoint.last_start_time)
      self.client.put(content)


# Represents a checkpoint.
# For compatibility, no fields must be deleted or assumed to be non-None.
Checkpoint = collections.namedtuple(
    'Checkpoint',
    [
        # (int) Next entry ID to process.
        'next_id',
        # (float) Timestamp in seconds from UNIX epoch when the last build
        # started.
        'last_start_time',
    ])


class CheckpointError(Exception):
  """Raised when a checkpoint is corrupted or not found."""
