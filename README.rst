====================
(GitLab) Auto Merger
====================

Robot script that automatically executes merge requests in GitLab.

Description
===========
GitLab Auto Merger is a script acting like a robot merger. 
To enable Auto Merger, you need to create an account named "Auto Merger"
and add it to your GitLab project/repository as a developer.
To perform auto merging, assign a merge request to Auto Merger. 
Then, the next time when Auto Merger is activated (potentially through a 
timed cron job), it will try to merge the commits into designated branch.

Notification emails will be sent to (human) developers either if the merge
is resolved or fails.

**NOTE THAT** Auto Merger was created in a rush, without even noticing the 
builtin one-click merging functionality of GitLab. In hindsight, it would
have been easier to simply use the one-click branch merging feature.
But it was created anyway.
