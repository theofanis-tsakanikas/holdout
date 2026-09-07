variable "region" {
  type        = string
  default     = "eu-west-1"
  description = "The AWS region the estate runs in. Asserted against what bootstrap applied."
}

variable "databricks_account_id" {
  type      = string
  sensitive = true
  # No default: it is an identifier and belongs in no committed file. `deploy` supplies it from
  # the `deploy` environment's secrets, where only a job that passes an approval can read it.
  description = "Databricks account id. No default: supplied at apply time."
}

variable "databricks_client_id" {
  type        = string
  sensitive   = true
  description = "Account service principal's client id. No default: half of a credential."
}

variable "databricks_client_secret" {
  type        = string
  sensitive   = true
  description = "Account service principal's OAuth secret. No default: it is a credential."
}

variable "warehouse_size" {
  type    = string
  default = "2X-Small"
  # **The smallest size Databricks offers, and the size is not the cost control — the auto-stop
  # is.** A serverless warehouse bills while it is running and nothing while it is stopped, so a
  # larger cluster that stops after ten minutes costs less than a small one left up. `CLAUDE.md`
  # models serverless SQL at 5–15 USD a cycle and this is the knob that keeps it there.
  description = "Serverless SQL warehouse size. The auto-stop below is what bounds the bill."
}

variable "warehouse_auto_stop_minutes" {
  type    = number
  default = 10
  # Ten minutes rather than the platform default of forty-five. A dashboard query wakes the
  # warehouse and a human reading the result is idle within minutes; forty-five minutes of idle
  # per glance is the difference between a demonstration and a bill.
  description = "Idle minutes before the warehouse stops. Ten, not the platform's forty-five."
}
