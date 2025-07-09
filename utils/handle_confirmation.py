import os
import requests
import re

def create_github_check(status, conclusion=None, title="", summary=""):
    """创建或更新GitHub检查状态"""
    github_token = os.getenv('GITHUB_TOKEN')
    repo_owner = os.getenv('REPO_OWNER')
    repo_name = os.getenv('REPO_NAME')

    # 获取PR的最新commit SHA
    pr_number = os.getenv('PR_NUMBER')
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    pr_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}'
    pr_response = requests.get(pr_url, headers=headers)
    commit_sha = pr_response.json()['head']['sha']

    data = {
        'name': 'Regression Test',
        'head_sha': commit_sha,
        'status': status,
        'output': {
            'title': title,
            'summary': summary
        }
    }

    if conclusion:
        data['conclusion'] = conclusion

    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/check-runs'
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def check_test_status(test_id):
    """检查测试状态"""
    api_key = os.getenv('THIRD_PARTY_API_KEY')
    url = f"https://third-party-api.com/test-status/{test_id}"

    headers = {
        'Authorization': f'Bearer {api_key}'
    }

    response = requests.get(url, headers=headers)
    return response.json()

def add_pr_comment(message):
    """在PR中添加评论"""
    github_token = os.getenv('GITHUB_TOKEN')
    repo_owner = os.getenv('REPO_OWNER')
    repo_name = os.getenv('REPO_NAME')
    pr_number = os.getenv('PR_NUMBER')

    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    data = {'body': message}

    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{pr_number}/comments'
    requests.post(url, headers=headers, json=data)

def main():
    try:
        # 从评论中提取测试ID
        comment_body = os.getenv('COMMENT_BODY', '')  # 需要在workflow中传递
        match = re.search(r'/confirm-regression\s+(\w+)', comment_body)

        if not match:
            add_pr_comment('❌ 无效的确认格式，请使用 `/confirm-regression <test_id>`')
            return

        test_id = match.group(1)

        # 重新检查测试状态
        status_result = check_test_status(test_id)
        status = status_result.get('status')
        result = status_result.get('result')

        if status == 'completed' and result == 'success':
            create_github_check('completed', 'success', '回归测试通过', '用户确认后测试通过')
            add_pr_comment(f'✅ 回归测试已确认通过\n\n测试ID: {test_id}')
        else:
            create_github_check('completed', 'failure', '回归测试仍未通过', '用户确认后测试仍未通过')
            add_pr_comment(f'❌ 回归测试仍未通过\n\n测试ID: {test_id}\n当前状态: {status}, 结果: {result}')

    except Exception as e:
        add_pr_comment(f'❌ 处理确认时发生错误: {str(e)}')

if __name__ == '__main__':
    main()