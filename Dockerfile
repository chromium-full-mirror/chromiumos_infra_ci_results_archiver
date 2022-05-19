# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

FROM ubuntu:18.04

WORKDIR /ci_results_archiver

RUN apt-get update && apt-get install -y \
    python-pip \
    default-libmysqlclient-dev \
    libssl-dev

RUN pip install apscheduler google-cloud \
                google-cloud-bigquery \
                google-cloud-datastore \
                google-cloud-kms \
                google-cloud-storage \
                MySQL-python \
                PyYAML subprocess32

COPY chromite /ci_results_archiver/chromite
COPY ci_results_archiver /ci_results_archiver/ci_results_archiver
