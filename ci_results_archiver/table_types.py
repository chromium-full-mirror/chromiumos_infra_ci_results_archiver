# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Enum of BigQuery table types."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import enum


class TableType(enum.Enum):
  """Enum of BigQuery table types."""

  TKO_JOBS = 'tko_jobs'
  AFE_JOBS = 'afe_jobs'
  CIDB_BUILDS = 'cidb_builds'
