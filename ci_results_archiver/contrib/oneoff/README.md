### One off BigQuery table updates

This package houses one off updates to ci_results_archiver BigQuery tables and
the GS dumps. Updates are generally not safe concurrent with the
ci_results_archiver execution because both try to update the BigQuery tables and
dumps without any synchronization.

It is recommended to temporaryily stop ci_results_archiver when running a
one off update operation.
