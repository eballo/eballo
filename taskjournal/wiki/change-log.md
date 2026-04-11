# Changelog

## 0.31.0

- #91 Improve week command

## 0.30.0

- #87 Improve Holidays command

## 0.29.0

- #87 Fix total time spent calculation

## 0.28.0

- fix jira issue - pagination

## 0.27.0

- Fix some sonar issues

## 0.26.0

- Add Mypy + fix issues

## 0.25.0

- Improve code coverage

## 0.24.0

- #75 Small improvements test

## 0.23.0

Improve JiraService + code coverage

## 0.22.0

- Improve Readme

## 0.21.0

- Add fireman weeks

## 0.20.0

- Improve get location from wifi service

## 0.19.0

- be able to get the pending tasks from previous week

## 0.18.0

- add statistics command

## 0.17.0

- add 1on1 report

## 0.16.0

- add holidays populate command

## 0.15.0

- add holidays command to manage holidays

## 0.14.0

- add migrate command to help migrate from older versions

## 0.13.0

- Add github URL to the Code Review section
- Validate if the PR was already reviewd

## 0.12.1

- Improve bump version to support (fix/major/minor versions)
- add changelog section

## 0.12.0

- add Jira link
- addd github repo link

## 0.11.0

- add work location
- add firefighter mode
- add use of jinja2 library

## 0.9.0

- Improve Github Service
    - Improve logging if it doesn't exist
    - migrate to async library
- update services + tests to use async calls

## 0.8.0

- Improve Jira Service
    - Improve logging if it doesn't exist
    - migrate to version 3 jsql
    - migrate to httpx to use async calls
- update services to use async calls

## 0.7.0

- Big refactor for cli (better structure and better organization for the commands)
- Introduce the CommandManager class + services

**Note** the versions do not match the github releases versions they start to be aligned from 0.5.0

### 0.6.0

- Add md template support

### 0.5.0

- Add github integration service

### 0.4.0

- Add backup command
- Jira integration
- Improve Templates (dailyNotes, retro, weeklysummary)
- daily-start with force option
- daily-finish with force option
- daily-start for a given date
- daily-finish for a given date
- Created Task model (pydantic) + refactor

### 0.3.0

- add daily-finish custom date update

### 0.2.0

- install package properly
- added proper packages

### 0.1.0

- Initial release
- Add daily start
- Add daily finish
- Add retro
- Add week summary
- Add time
- tests + code coverage
- pre-commit
- shell completion
