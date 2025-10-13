# This file is the basis of syncing files between the two Globus endpoints.
# It is called by the cron job in cron.sh
# For more information on the flags used here, see: https://docs.globus.org/cli/reference/transfer/
# Or you can look at ./setup.sh for more comments on the flags.

NEU="686bbc3e-08f7-46cf-95f8-7539e6fee972"
UI="39dd0982-d784-11e6-9cd4-22000a1e3b52"
globus transfer --recursive --sync-level mtime --label "NEU to UI sync" $NEU:/ $UI:/Shared/vosslabhpc/Projects/BOOST/InterventionStudy/3-experiment/data/ne-dump --notify on --preserve-mtime

