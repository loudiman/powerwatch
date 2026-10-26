---
status: proposed
---

# Sandbox versus billing for the BigQuery project

The project runs on the BigQuery sandbox (billing disabled). The sandbox forces a 60-day expiry on every table and view and BigQuery refuses any longer value ("Billing has not been enabled for this project ... must be less than 60 days", observed 2026-10-26 at both dataset and table level), and it does not support DML statements. That expiry deleted the whole warehouse in August 2026 (docs/postmortem-2026-10.md).

**Recommendation:** enable billing on `powerwatch-2026ldm`, then clear the dataset's default expiry (the loader's preflight does this on its next run) and set a budget alert. Cost at this size is zero: BigQuery's free tier is 10 GiB of storage and 1 TiB of queries per month with no end date, a full rebuild bills 0.44 GB, and the warehouse stores about 0.3 GB. Only Vertex AI calls from the assistant would be billed, at cents per question.

**Until that decision is made, the project stays on the sandbox and survives by rebuild:** the scheduled GitHub Actions workflow reloads and rebuilds the warehouse weekly with `ALLOW_SANDBOX=1`, which resets the 60-day clock and doubles as the freshness canary. This path rules out any model that needs DML, so incremental materializations stay off the table (ADR-0002) while the sandbox stands.

## Considered options

- **Enable billing.** Removes the expiry and the DML ban. Needs a billing account and a budget alert; the owner must do it. Preferred.
- **Stay on the sandbox, rebuild on a schedule.** Free, already implemented, but a missed month of rebuilds kills the demo again, and every rebuild is a full reload.
- **Stay on the sandbox, rebuild by hand.** What happened in 2026. Rejected.
