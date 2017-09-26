# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Manages "next ID" to process."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from google.cloud import exceptions  # pylint: disable=import-error,no-name-in-module


class Checkpoint(object):
  """Manages "next ID" to process.

  "Next ID" identifies primary ID of the oldest unprocessed entry in the
  source database. On a successful run of the BigQuery table builder pipeline,
  (maximum ID of entries processed in a run) + 1 will be saved as a next ID,
  and on a next run it is read to continue processing subsequent entries.

  Data is saved in Google Cloud Storage.
  """

  def __init__(self, bucket, dataset, table_prefix):
    """Initializes the checkpoint object.

    Args:
      bucket: google.cloud.storage.Bucket object.
      dataset: BigQuery dataset name.
      table_prefix: BigQuery table prefix.
    """
    self._bucket = bucket
    path = 'checkpoints/next_id.%s.%s' % (dataset, table_prefix)
    self._blob = bucket.blob(path)

  def LoadNextId(self):
    """Loads a next ID.

    Returns:
      An integer representing a next ID. If a checkpoint is not found on
      storage, 0 is returned.

    Raises:
      CheckpointNotFoundError: When the checkpoint is not found.
    """
    try:
      content = self._blob.download_as_string()
    except exceptions.NotFound:
      url = 'gs://%s/%s' % (self._blob.bucket.name, self._blob.name)
      raise CheckpointNotFoundError(
          'Checkpoint file is not found at %(url)s. '
          'If this is the first run, please create one manually with '
          'the follow command: '
          'gsutil -m cp <(echo INITIAL_ID) %(url)s' % {'url': url})
    return int(content)

  def SaveNextId(self, next_id):
    """Saves a next ID.

    Args:
      next_id: An integer representing a next ID.
    """
    assert isinstance(next_id, (int, long))
    self._blob.upload_from_string(str(next_id))


class CheckpointNotFoundError(Exception):
  """Raised when a checkpoint is not found."""
