import os
import requests
import json
import time
import hashlib
from github import Github


def trigger_test(payload):
    url = "https://webhooks.aftership.com/datarecce/webhooks/recce_check"
    response = requests.post(url, json=payload)
    return response.json()


def check_test_status(test_id):
    """检查测试状态"""
    api_key = os.getenv('API_KEY')
    url = f"https://webhooks.aftership.com/recce/{test_id}/api/checks"

    headers = {
        'api-key': api_key
    }
    check_list = []
    try:
        response = requests.get(url, headers=headers)
        if response.status_code >= 400:
            return False, check_list
    except requests.RequestException as e:
        if e.response.status_code == 404:
            print(f"waiting for regression test(id:{test_id}) to start, please wait...")
            return False, check_list
        else:
            print(f"error requesting regression test status: {e}")
        return False, check_list
    checks = response.json()
    flag = True
    for check in checks:
        check_name = check.get('name')
        is_checked = check.get('is_checked')
        check_list.append({
            "check_name": check_name,
            "is_checked": is_checked
        })
        if not is_checked:
            flag = False
            # print(f"【{check_name}】 is not checked")
    return flag, check_list


def get_existing_comment_id():
    """获取现有的回归测试评论ID"""
    github_token = os.getenv('GITHUB_TOKEN')
    repo_owner = os.getenv('REPO_OWNER')
    repo_name = os.getenv('REPO_NAME')
    pr_number = int(os.getenv('PR_NUMBER'))

    g = Github(github_token)
    repo = g.get_repo(f"{repo_owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    for comment in pr.get_issue_comments():
        if 'Regression Test Status' in comment.body:
            return comment

    return None


def update_or_create_pr_comment(check_list):
    """更新或创建PR评论"""
    github_token = os.getenv('GITHUB_TOKEN')
    repo_owner = os.getenv('REPO_OWNER')
    repo_name = os.getenv('REPO_NAME')
    pr_number = int(os.getenv('PR_NUMBER'))

    g = Github(github_token)
    repo = g.get_repo(f"{repo_owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    if check_list:
        message = f"## Regression Test Status 🔄\n\n"
        incomplete_checks = []
        for check in check_list:
            check_name = check.get('check_name')
            is_checked = check.get('is_checked')
            if is_checked:
                message += f"- ✅ {check_name}\n"
            else:
                message += f"- ❌ {check_name}\n"
                incomplete_checks.append(check_name)

        if not incomplete_checks:
            message += f"\n## Regression Test Status ✅\n\nAll checks completed!"

        message += f"\n\n*Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}*"
    else:
        message = f"## Regression Test Status ✅\n\nAll checks completed!\n\n*Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}*"

    existing_comment = get_existing_comment_id()

    if existing_comment:
        # 更新现有评论
        existing_comment.edit(message)
    else:
        # 创建新评论
        pr.create_issue_comment(message)


def main():
    print('-------- regression check running ---------')
    try:
        repo_name = os.getenv('REPO_NAME')
        pr_number = os.getenv('PR_NUMBER')
        if not repo_name or not pr_number:
            raise ValueError("REPO_NAME and PR_NUMBER environment variables must be set.")

        # test_id = hashlib.md5(f"{repo_name}_{pr_number}".encode()).hexdigest()
        test_id = '2ec238177b518e0d2fed7dec4fa02c22'

        while True:
            # 轮询检查状态（最多10分钟）
            max_attempts = 120  # 10分钟，每5秒检查一次
            for attempt in range(max_attempts):
                is_checked, check_list = check_test_status(test_id)
                if check_list:
                    # 在PR中添加/修改评论，列出未检查的检查项
                    update_or_create_pr_comment(check_list)
                if is_checked:
                    return "pass"
                time.sleep(5)

            # 超时处理
            is_checked, check_list = check_test_status(test_id)
            if is_checked:
                return "pass"
            else:
                if check_list:
                    continue
                else:
                    # 重新触发测试 todo
                    print("？？？No checks found, re-triggering the test...")
                    # github_context = os.getenv('GITHUB_CONTEXT')
                    # payload = json.loads(github_context).get('event', {})
                    # if payload:
                    #     trigger_test(payload)
                    # else:
                    #     print("No payload found in GITHUB_CONTEXT, cannot re-trigger the test.")


    except Exception as e:
        pass


if __name__ == '__main__':
    main()
