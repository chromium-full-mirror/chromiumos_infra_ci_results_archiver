# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# local dir
local_dir = $(shell pwd)
cmddir = $(local_dir)/cmd

# Cloud Project to build and store the docker images in.
ORG_PREFIX = google.com
PROJECT = chromeos-lab
GCS_BUCKET = chromeos-ci-results

# Download service account to call BQ API. You must have appropirate
# perssion of the bucket assigned above.
load-credentials:
	if [ ! -f ./service_account.json ]; then \
		gsutil cp gs://$(GCS_BUCKET)/cred/service_account.json .; \
	fi

.create-cmddir:
	rm -rf $(cmddir)
	mkdir -p $(cmddir)

.load-chromite:
	if [ ! -d ./chromite ]; then \
		git clone https://chromium.googlesource.com/chromiumos/chromite ; \
	fi

.load-libs: .load-chromite
	pip install apscheduler gcloud \
				google-cloud-bigquery \
				google-cloud-datastore \
				google-cloud-kms \
				google-cloud-storage \
				MySQL-python \
				PyYAML subprocess32 \
				pytest pytest-cov

.setup-cmddir: .create-cmddir .load-chromite
	cp Dockerfile $(cmddir)/
	cp -r ci_results_archiver $(cmddir)/
	cp config $(cmddir)/
	cp service_account.json $(cmddir)/
	cp -r chromite $(cmddir)/

# Run ci_results_archiver in current path, not docker.
run-local: .load-libs
	export GOOGLE_APPLICATION_CREDENTIALS=service_account.json; \
	export PYTHONPATH=`pwd`; \
	python ci_results_archiver/main.py -c config --one-shot --table-type tko_jobs

# Run unit test.
unit-test: .load-libs load-credentials
	export GOOGLE_APPLICATION_CREDENTIALS=$(local_dir)/service_account.json; \
	python -m pytest ./ci_results_archiver/

# Build docker image locally.
local-build: .setup-cmddir
	sudo docker build -t gcr.io/$(ORG_PREFIX)/$(PROJECT)/ci_results_archiver \
		-f $(cmddir)/Dockerfile $(cmddir)

# Build docker image on GCP.
cloud-build: .setup-cmddir
	gcloud builds submit \
		--tag gcr.io/$(ORG_PREFIX)/$(PROJECT)/ci_results_archiver \
		--project $(ORG_PREFIX):$(PROJECT) \
		$(cmddir)
