# ci_scripts
This repository contains various scripts (mostly AI-generated) to enumerate data from public APIs of CI tools such as GitHub and CircleCI.

- get-github-artifacts.py: Download all GitHub workflow artifacts for an organization 
- get-github-workflow-PRs.py: Identify workflows triggered by PRs from forks to check whether manual approval was required before workflow execution
- get-circleci-artifacts.py: Download all CircleCI pipeline artifacts from jobs in projects with the same names as an organization's GitHub repos
