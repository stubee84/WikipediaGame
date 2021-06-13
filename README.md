### Wikipedia Game ###

**Overview**

A resursive application which searches wikipedia for specific links. The criteria is provided by CLI.

**Description**

1. Using the starting link the application searches through Wikipedia's publicly available REST API and gathers a source of initial links.
2. For every returned link of from the source of initial link an individual thread is spawned.
3. Thhese threads recursively search through those links for the end link.
4. Once the end link is found the application stops. Cancels the other threads and returns the list of all links.


**How to Run**

From command enter python3 game.py <start> <end>
ex: python3 game.py "Web Bot" "Tax History"