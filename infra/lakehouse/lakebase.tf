# **Lakebase — the operational store, and the one thing here that bills while it exists.**
#
# `CLAUDE.md` splits the two stores by the question they answer: Lakebase answers *what do I do
# now* and holds only the current operational state; the lakehouse answers *what happened and what
# did I learn* and holds everything, forever. The decision path writes its record to Lakebase
# before dispatching a price, and features flow the other way.
#
# **It is in this layer rather than in `foundation` because its lifetime is the lakehouse's.** A
# teardown that left it standing would leave the one resource in this estate that bills at rest,
# which is exactly what `destroy` exists to prevent and what the TTL reaper collects.
resource "databricks_database_instance" "lakebase" {
  provider = databricks.workspace

  name = "holdout"

  # **The smallest capacity, and it is the whole cost decision.** `CLAUDE.md` models Lakebase at
  # 2–8 USD per cycle; the capacity below is what keeps it there. A decision path taking 2.4M
  # decisions a day is the scenario, not this estate — the corpus is 100 stores over a driven day.
  capacity = "CU_1"
}
