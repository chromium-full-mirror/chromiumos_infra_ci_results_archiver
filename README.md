# ci_results_archvier

## Setup

1. Install mysql client:

        sudo apt-get install default-libmysqlclient-dev

1. Install python libs:

        make load-libs

### Known Issues

1. `_mysql.c:2005:41: error: 'MYSQL' {aka 'struct st_mysql'} has no member named 'reconnect'`:

   This may happen on Debian based system.
   Workaround: Run `sudo sed '/st_mysql_options options;/a unsigned int reconnect;' /usr/include/mysql/mysql.h -i.bkp`.

## Unit test

1. Run unit test:

        make unit-test

## E2E test

1. Configure your db information into the `config-dev` file:

tko:
  credentials:
    hostname: your_sql_instance_ip
    username: sql_use
    password: sql_password
    database: sql_db_name
    timezone: US/Pacific

1. Run `ci_results_archiver` locally:

        make run-local

Note, this will run in one-shot mode with the dev config. Make sure your
desktop IP has been whitelisted by the TKO Cloud SQL instance. To export data to BigQuery,
you need a service account json key in the folder. For internal users, run
`make load-credentials` first.

## Build the docker

1. Build the docker locally:

        make local-build

1. Build docker on GCP:

        make cloud-build

By default it creates the image to project `google.com:chromeos-lab`. If this is not your
preference, please configure it in `Makefile`.

## Deploy to GKE cluster

If you want to deploy the docker to ChromeOS Lab project, please refer our
[internal doc](https://g3doc.corp.google.com/company/teams/chrome/ops/chromeos/test_infra/test_platform/for_team_members/ci_results_archiver.md?cl=head) for more details.
