import os
import requests
import json
import time
import hashlib


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
    no_check_names = []
    try:
        response = requests.get(url, headers=headers)
        if response.status_code >= 400:
            return False, no_check_names
    except requests.RequestException as e:
        if e.response.status_code == 404:
            print(f"waiting for regression test(id:{test_id}) to start, please wait...")
            return False, no_check_names
        else:
            print(f"error requesting regression test status: {e}")
        return False, no_check_names
    checks = response.json()
    flag = True
    for check in checks:
        check_name = check.get('name')
        is_checked = check.get('is_checked')
        if not is_checked:
            flag = False
            no_check_names.append(check_name)
            print(f"【{check_name}】 is not checked")
    return flag, no_check_names


def get_existing_comment_id():
    """获取现有的回归测试评论ID"""
    github_token = os.getenv('GITHUB_TOKEN')
    repo_owner = os.getenv('REPO_OWNER')
    repo_name = os.getenv('REPO_NAME')
    pr_number = os.getenv('PR_NUMBER')

    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{pr_number}/comments'
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        comments = response.json()
        for comment in comments:
            if 'Regression Test Status' in comment.get('body', ''):
                return comment['id']

    return None


def update_or_create_pr_comment(no_check_names):
    """更新或创建PR评论"""
    github_token = os.getenv('GITHUB_TOKEN')
    repo_owner = os.getenv('REPO_OWNER')
    repo_name = os.getenv('REPO_NAME')
    pr_number = os.getenv('PR_NUMBER')

    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    if no_check_names:
        message = f"## Regression Test Status 🔄\n\nThe following checks are not completed:\n"
        for name in no_check_names:
            message += f"- ❌ {name}\n"
        message += f"\n*Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}*"
    else:
        message = f"## Regression Test Status ✅\n\nAll checks completed!\n\n*Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}*"

    data = {'body': message}

    existing_comment_id = get_existing_comment_id()

    if existing_comment_id:
        url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/issues/comments/{existing_comment_id}'
        requests.patch(url, headers=headers, json=data)
    else:
        url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{pr_number}/comments'
        requests.post(url, headers=headers, json=data)


def main():
    print('-------- regression check running ---------')
    try:
        repo_name = os.getenv('REPO_NAME')
        pr_number = os.getenv('PR_NUMBER')
        if not repo_name or not pr_number:
            raise ValueError("REPO_NAME and PR_NUMBER environment variables must be set.")

        test_id = hashlib.md5(f"{repo_name}_{pr_number}".encode()).hexdigest()

        while True:
            # 轮询检查状态（最多10分钟）
            max_attempts = 120  # 10分钟，每5秒检查一次
            for attempt in range(max_attempts):
                is_checked, no_check_names = check_test_status(test_id)
                if is_checked:
                    return "pass"
                else:
                    if no_check_names:
                        # 在PR中添加/修改评论，列出未检查的检查项
                        update_or_create_pr_comment(no_check_names)
                time.sleep(5)

            # 超时处理
            is_checked, no_check_names = check_test_status(test_id)
            if is_checked:
                return "pass"
            else:
                if no_check_names:
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
