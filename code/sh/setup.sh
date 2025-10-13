# This file is the setup to create the sync and specify permissions.
# It is called once to set up the sync.
# It is important to note that actually running the sync can only be done by an individual user, not a group.
# Therefore, we create a group for the UI team to manage the destination endpoint (UI final directory) and these members can then run the sync as needed.

# These are the endpoints for the NE and UI Globus shares. You can find these by using the following command:
globus endpoint search "uiowadata" # Choose the top one here
globus endpoint search "BOOST" # Choose the one with 'neu.edu' as the domain for the "Owner" column

# You can then save them as variables for easier use. I'm not sure if these are static or if they change over time, so you may want to check them again in the future.
NEU="686bbc3e-08f7-46cf-95f8-7539e6fee972"
UI="39dd0982-d784-11e6-9cd4-22000a1e3b52"

# This creates a Globus group for the UI team to manage the sync. All members of the group will be able to manage the sync.
globus group create  --description "BOOST Intervention Globus Transfer group - the UI team group for the sync" NAME="boost-int-ui"


# Add group members as admins, so they can manage the sync. 
EXAMPLE_EMAIL="test@test.com" # Replace with an actual uiowa email
globus group member add --role admin 7945f56e-a845-11f0-865d-0affc8a7155b zjgilliam@uiowa.edu
globus group member add --role admin 7945f56e-a845-11f0-865d-0affc8a7155b mwvoss@uiowa.edu
globus group member add --role admin 7945f56e-a845-11f0-865d-0affc8a7155b $EXAMPLE_EMAIL 


# Dry run to see what would be transferred
# The flags mean:
#   --recursive: transfer all files and directories recursively
#   --sync-level mtime: only transfer files that are new or have been modified (based on modification time)
#   --label: a label for the transfer task
#   --notify on: send a notification when the transfer is complete
#   --dry-run: do not actually perform the transfer, just show what would be done
#   --preserve-mtime: preserve the modification time of the files being transferred (So the source modification times are kept in the destination)
globus transfer --recursive --sync-level mtime --label "NEU to UI sync" $NEU:/ $UI:/Shared/vosslabhpc/Projects/BOOST/InterventionStudy/3-experiment/data/ne-dump --notify on -- preserve-mtime --dry-run

# After checking that the paths and arguments look correct, run the actual transfer
# These have the same flags as above, but without the --dry-run flag
globus transfer --recursive --sync-level mtime --label "NEU to UI sync" $NEU:/ $UI:/Shared/vosslabhpc/Projects/BOOST/InterventionStudy/3-experiment/data/ne-dump --notify on --preserve-mtime

# To view the status of the transfer, use the task ID from the output of the above command and run the below
TEST_TASK_ID="68ffa624-a846-11f0-bf3c-0e092d85c59b" # Replace with your actual task ID
globus task show $TEST_TASK_ID

