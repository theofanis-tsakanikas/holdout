#!/usr/bin/env bash
# Start a Databricks job, wait for it, and — when it fails — say what failed.
#
# **This exists because a failure said nothing.** `backfill`'s first real dispatch ended with:
#
#     Error: failed to reach TERMINATED or SKIPPED, got INTERNAL_ERROR:
#     Task history failed with message: Workload failed, see run output for details.
#
# *See run output for details* is advice to open a console, and `CLAUDE.md`'s rule is **IaC only,
# no console actions, ever** — which is a rule about changing things, but the diagnosis had the
# same shape: the only place the error existed was a page. A workflow that spends an environment
# approval, assumes a role and starts an hour of compute, and then reports that something went
# wrong somewhere, has moved the failure out of the log and into a browser.
#
# So on failure this fetches the run, prints every task's state, and prints the output of each
# task that did not succeed. The exit code is unchanged: a failed job still fails the step.
#
# **One script rather than a shell function per workflow.** `backfill.yml` and `run.yml` both
# start jobs, and two copies of this would be two things to keep equal — which is the defect
# this repository has now filed under three different names.
set -euo pipefail

id="$1"
label="${2:-job $1}"

echo "── ${label} (job ${id})"
if databricks jobs run-now "$id" --timeout 3h; then
  exit 0
fi

echo "── ${label} FAILED; fetching what the job said"

# The most recent run of this job. `run-now --timeout` does not hand back an id on the failing
# path, and the job is started once per step, so the latest run is this one.
run_id=$(databricks jobs list-runs --job-id "$id" --limit 1 --output json | jq -r '.runs[0].run_id // empty')
if [ -z "$run_id" ]; then
  echo "::error::no run found for job ${id}. It may not have started at all."
  exit 1
fi

run=$(databricks jobs get-run "$run_id" --output json)
echo "   run page: $(echo "$run" | jq -r '.run_page_url // "-"')"
echo "$run" | jq -r '
  .tasks[]
  | "   " + .task_key
    + "  " + (.state.result_state // .state.life_cycle_state // "?")
    + "  " + ((.state.state_message // "") | .[0:300])'

# **Every task that did not succeed, not just the first.** A job whose second task failed because
# its first did is two facts, and reporting one of them sends whoever reads this to the wrong
# file. `pipelines/ml/promotion.py` reports every gate that refused for the same reason.
for task in $(echo "$run" | jq -r '.tasks[] | select((.state.result_state // "") != "SUCCESS") | .run_id'); do
  echo "── output of task run ${task}"
  databricks jobs get-run-output "$task" --output json \
    | jq -r '[(.error // empty), (.error_trace // empty), (.logs // empty)] | join("\n")' \
    | tail -n 200
done

exit 1
