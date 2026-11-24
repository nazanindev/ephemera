#!/bin/sh
# One auto-walk: refresh corpora, sync post fates, walk + screen + post, print metrics.
# Entry point of the Railway cron service (backend/publisher.Dockerfile). Must exit when
# done — Railway skips the next scheduled run while a previous one is still alive.
#   EPHEMERA_COUNT       how many experiment runs (default 8)
#   EPHEMERA_POST_STATE  published | queue | draft (default published)
set -u

python -m app.publisher.publish refresh-corpora || exit 1
python -m app.publisher.publish sync || true

python -m app.publisher.publish run \
  --experiment random \
  --count "${EPHEMERA_COUNT:-8}" \
  --state "${EPHEMERA_POST_STATE:-published}"
rc=$?

# the distribution the walk is producing (shape / mode / source), so drift shows in the log
python -m app.publisher.publish metrics || true
exit $rc
