from github import Github
import os, time


github_token = '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'
repo_owner = 'Mr-KIDBK'
repo_name = 'test_dbt'
pr_number = 6

def get_existing_comment_id():
    """获取现有的回归测试评论ID"""

    g = Github(github_token)
    repo = g.get_repo(f"{repo_owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    for comment in pr.get_issue_comments():
        if 'Regression Test Status' in comment.body:
            return comment

    return None

def update_or_create_pr_comment():
    """更新或创建PR评论"""


    g = Github(github_token)
    repo = g.get_repo(f"{repo_owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    message = f"## Regression Test Status 🔄\n\n"
    message += f"- ✅ All checks completed!22222\n"

    existing_comment = get_existing_comment_id()

    if existing_comment:
        # 更新现有评论
        existing_comment.edit(message)
    else:
        # 创建新评论
        pr.create_issue_comment(message)

update_or_create_pr_comment()