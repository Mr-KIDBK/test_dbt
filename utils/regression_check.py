import os
import requests
import json
import time

def create_github_check(status, conclusion=None, title="", summary=""):
    """创建或更新GitHub检查状态"""
    github_token = os.getenv('GITHUB_TOKEN')
    repo_owner = os.getenv('REPO_OWNER')
    repo_name = os.getenv('REPO_NAME')
    commit_sha = os.getenv('COMMIT_SHA')
    
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
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

def trigger_third_party_test():
    """触发回归测试"""
    api_key = os.getenv('THIRD_PARTY_API_KEY')
    # 替换为实际的第三方API端点
    url = "https://third-party-api.com/regression-test"
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'repo_owner': os.getenv('REPO_OWNER'),
        'repo_name': os.getenv('REPO_NAME'),
        'commit_sha': os.getenv('COMMIT_SHA'),
        'pr_number': os.getenv('PR_NUMBER')
    }
    
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
    print('---------- 开始回归测试检查 ---------')
    try:
        # 创建初始检查状态
        create_github_check('in_progress', title='回归测试进行中', summary='正在触发回归测试...')
        
        # 触发第三方测试
        test_result = trigger_third_party_test()
        test_id = test_result.get('test_id')
        
        if not test_id:
            create_github_check('completed', 'failure', '测试触发失败', '无法触发测试')
            return

        # 轮询检查状态（最多10分钟）
        max_attempts = 120  # 10分钟，每5秒检查一次
        for attempt in range(max_attempts):
            status_result = check_test_status(test_id)
            status = status_result.get('status')
            
            if status == 'completed':
                result = status_result.get('result')
                if result == 'success':
                    create_github_check('completed', 'success', '回归测试通过', '所有测试检查通过')
                    return
                else:
                    # 测试失败，等待用户确认
                    create_github_check('completed', 'failure', '回归测试失败', 
                                      f'测试失败，请在确认后评论 `/confirm-regression {test_id}` 来重新检查')
                    add_pr_comment(f'🔴 回归测试失败\n\n'
                                 f'测试ID: {test_id}\n'
                                 f'请前往确认测试结果，如果确认通过，请评论 `/confirm-regression {test_id}`')
                    return
            elif status == 'failed':
                create_github_check('completed', 'failure', '测试执行失败', '测试执行失败')
                return
            
            time.sleep(5)
        
        # 超时处理
        create_github_check('completed', 'failure', '测试超时', 
                          f'测试超时，请在确认后评论 `/confirm-regression {test_id}` 来重新检查')
        add_pr_comment(f'⏰ 回归测试超时\n\n'
                     f'测试ID: {test_id}\n'
                     f'请前往确认测试结果，如果确认通过，请评论 `/confirm-regression {test_id}`')
        
    except Exception as e:
        create_github_check('completed', 'failure', '检查执行错误', f'错误: {str(e)}')

if __name__ == '__main__':
    main()