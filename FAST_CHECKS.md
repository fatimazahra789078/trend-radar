# Checks every 15 minutes (instead of about once an hour)

GitHub runs scheduled jobs "best effort": the `*/15` schedule really runs about **once an hour**. A free outside
timer can start the check every 15 minutes through GitHub's official API. Two checks never overlap (the workflow
waits for the previous one), so nothing breaks if both the schedule and the timer fire.

You do this once, about 5 minutes. I can't do it for you: it needs your own GitHub token and an account on the timer site.

## 1. A GitHub token that can only start this one workflow

1. Open **https://github.com/settings/personal-access-tokens/new** (fine-grained token).
2. **Token name:** `trend-radar-timer` · **Expiration:** 1 year.
3. **Repository access:** *Only select repositories* → `trend-radar`.
4. **Permissions → Repository permissions → Actions:** *Read and write*. Nothing else.
5. **Generate token** and copy it (starts with `github_pat_`). Keep it secret.

## 2. The timer (cron-job.org, free)

1. Create a free account on **https://cron-job.org** and click **Create cronjob**.
2. **URL:** `https://api.github.com/repos/fatimazahra789078/trend-radar/actions/workflows/radar.yml/dispatches`
3. **Execution schedule:** every 15 minutes.
4. **Advanced:**
   - **Request method:** `POST`
   - **Headers:**
     - `Authorization` = `Bearer github_pat_...` (your token)
     - `Accept` = `application/vnd.github+json`
     - `X-GitHub-Api-Version` = `2022-11-28`
   - **Request body:** `{"ref":"main"}`
5. **Save** → **Test run**. A good answer is **HTTP 204** (no content). Then GitHub → `trend-radar` → **Actions** shows a new "Trend Radar" run.

## Good to know

- Cost: free (public repository).
- To stop: disable the job on cron-job.org, or delete the token on GitHub.
- If the token expires, the hourly schedule keeps working; only the extra checks stop.
