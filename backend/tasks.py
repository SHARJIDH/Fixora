from datetime import datetime
from services.github_service import GitHubService
from services.ai_service import AIService
from services.groq_service import GroqService
from services.pr_service import PRService
from services import db as database
from services.redis_service import set_job_cache
from utils.logger import get_logger

logger = get_logger(__name__)


def create_ai_service(config, user_model=None):
    if config.get('use_openrouter'):
        return AIService(api_key=config.get('openrouter_key'), model=user_model)
    return GroqService(api_key=config.get('groq_key'))


def persist_job(job):
    job_id = job.get('id')
    if job_id:
        set_job_cache(job_id, job)

    if database.is_db_available():
        existing = database.get_job_by_id(job_id)
        if existing:
            database.update_job(job_id, job)
        else:
            database.insert_job(job)
        return

    logger.info("job_saved_without_db", job_id=job.get('id'), status=job.get('status'))

def build_initial_job(params):
    return {
        'id': params['job_id'],
        'repo': params['repo_full_name'],
        'issueNumber': params.get('issue_number'),
        'issueTitle': params.get('issue_title') or f"Manual Task: {params.get('prompt', '')[:50]}...",
        'user_id': params.get('user_id'),
        'status': 'processing',
        'stage': 'generating',
        'retryCount': 0,
        'createdAt': datetime.now().isoformat(),
        'prUrl': None,
        'error': None,
        'logs': [params.get('initial_log', 'Job started via RQ')],
        'validationLogs': []
    }


def finalize_job_success(job, result):
    job['status'] = 'completed' if result.get('success') else 'failed'
    job['completedAt'] = datetime.now().isoformat()
    job['prUrl'] = result.get('pr_url')
    job['error'] = result.get('message') if not result.get('success') else None
    job['validationLogs'] = result.get('validation_logs', [])
    job['stage'] = 'completed' if result.get('success') else 'failed'
    result_msg = 'PR created' if result.get('success') else result.get('message', 'Failed')
    job['logs'].append(f"Result: {result_msg}")
    return job


def finalize_job_error(job, error):
    job['status'] = 'failed'
    job['completedAt'] = datetime.now().isoformat()
    job['stage'] = 'error'
    job['error'] = str(error)
    job['logs'].append(f'Error: {str(error)}')
    return job


def process_webhook_task(params):
    job = build_initial_job({
        'job_id': params['job_id'],
        'repo_full_name': params['repo_full_name'],
        'issue_number': params['issue_number'],
        'issue_title': params['issue_title'],
        'initial_log': 'Job started via RQ'
    })

    try:
        github_service = GitHubService(params['github_token'])
        ai_service = create_ai_service(params['config'])
        pr_service = PRService(github_service, ai_service)

        if params['is_pr']:
            job['logs'].append('AI analyzing PR feedback...')
            persist_job(job)
            result = pr_service.process_pr_comment(
                repo_full_name=params['repo_full_name'],
                pr_number=params['issue_number'],
                comment_body=params['comment_body'],
                job_id=params['job_id']
            )
        else:
            job['logs'].append('AI analyzing issue...')
            persist_job(job)
            result = pr_service.process_issue(
                repo_full_name=params['repo_full_name'],
                issue_number=params['issue_number'],
                issue_title=params['issue_title'],
                issue_body=params['issue_body'],
                comment_body=params['comment_body'],
                job_id=params['job_id']
            )

        job = finalize_job_success(job, result)
        persist_job(job)
        return result

    except Exception as e:
        logger.error("webhook_task_failed", error=str(e), job_id=params['job_id'])
        job = finalize_job_error(job, e)
        persist_job(job)
        return {'success': False, 'message': str(e)}

def process_manual_task(params):
    job = build_initial_job({
        'job_id': params['job_id'],
        'repo_full_name': params['repo_full_name'],
        'user_id': params['user_id'],
        'prompt': params['prompt'],
        'initial_log': 'Manual job started via RQ'
    })
    persist_job(job)

    try:
        github_service = GitHubService(params['github_token'])
        ai_service = create_ai_service(params['config'])
        pr_service = PRService(github_service, ai_service)

        result = pr_service.process_manual_task(
            repo_full_name=params['repo_full_name'],
            prompt=params['prompt'],
            user_id=params['user_id'],
            job_id=params['job_id']
        )

        job = finalize_job_success(job, result)
        persist_job(job)
        return result

    except Exception as e:
        logger.error("manual_task_failed", error=str(e), job_id=params['job_id'])
        job = finalize_job_error(job, e)
        persist_job(job)
        return {'success': False, 'message': str(e)}
