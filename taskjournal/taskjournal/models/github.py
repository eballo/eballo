from pydantic import BaseModel


class RepoCommitStat(BaseModel):
    repo: str
    your_commits: int
    total_commits: int
    percentage: float


class PullRequest(BaseModel):
    number: int
    title: str
    repo: str
    url: str
    author: str
