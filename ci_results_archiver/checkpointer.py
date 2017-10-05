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


class Checkpointer(object):
  """Manages checkpoints.

  A checkpoint is a JSON file on Google Cloud Storage containing various
  information persisted between builder runs.

  The most important information in a checkpoint is "Next ID" which identifies
  the primary ID of the oldest unprocessed entry in the source database.
  On a successful run of the BigQuery table builder pipeline,
  (maximum ID of entries processed in a run) + 1 will be saved as a next ID,
  and on a next run it is read to continue processing subsequent entries.
  """

  def __init__(self, bucket, dataset, table_prefix):
    """Initializes the checkpointer object.

    Args:
      bucket: google.cloud.storage.Bucket object.
      dataset: BigQuery dataset name.
      table_prefix: BigQuery table prefix.
    """
    self._bucket = bucket
    path = 'checkpoints/checkpoint.%s.%s.json' % (dataset, table_prefix)
    self._blob = bucket.blob(path)

  def Load(self):
    """Loads a checkpoint.

    Returns:
      Checkpoint object.

    Raises:
      CheckpointError: When the checkpoint is corrupted or not found.
    """
    try:
      content = self._blob.download_as_string()
    except exceptions.NotFound:
      url = 'gs://%s/%s' % (self._blob.bucket.name, self._blob.name)
      raise CheckpointError(
          'Checkpoint file is not found at %(url)s. '
          'If this is the first run, please create one manually with '
          'gsutil command.' % {'url': url})
    data = json.loads(content)
    checkpoint = Checkpoint(
        next_id=data.get('next_id'),
        last_start_time=data.get('last_start_time'))
    if not checkpoint.next_id:
      raise CheckpointError('Checkpoint file is corrupted: next_id is not set.')
    return checkpoint

  def Save(self, checkpoint):
    """Saves a checkpoint.

    Args:
      checkpoint: Checkpoint object to be saved to the checkpoint JSON file.
    """
    self._blob.upload_from_string(json.dumps(checkpoint._asdict()))


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
