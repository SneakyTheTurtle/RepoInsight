import os
import subprocess
from datetime import datetime
import git
import time
from git import Repo
import argparse
import requests

NUM_CONTRIBUTORS_PRINTED = 6

CUTOFF_TIME_RECENT = int(time.time()) - (3 * 30 * 24 * 60 * 60) # Three months

num_commits = 0
num_empty_commits = 0
num_contributors = 0
num_branches = 0
num_tags = 0

num_commits_upstream = 0

author_stats = {}
author_stats_recent = {}

repo_activity_stats = {}

github_pat = os.environ.get('GITHUB_PAT')
if not github_pat:
    raise ValueError("Environment variable GITHUB_PAT not set!")

def get_upstream_repo_details(group_url, repo_name):
    owner = group_url.rstrip('/').split('/')[-1]
    headers = {
        'Authorization': f'token {github_pat}'
    }
    response = requests.get(f'https://api.github.com/repos/{owner}/{repo_name}', headers=headers)
    response_data = response.json()
    # print(f"Getting upstream repo details. Parent: {response_data.get('parent', {})}")
    return response_data.get('parent', {})

def ensure_repo_cloned(group_url, repo_name):
    if not os.path.exists(repo_name):
        print('Repository not cloned yet, doing so now...')
        subprocess.run(['git', 'clone', group_url + repo_name, repo_name])

def load_all_commit_hashes(local_path):
    repo = Repo(local_path)
    return [commit.hexsha for commit in repo.iter_commits()]

parser = argparse.ArgumentParser(description="Collect stats from GitHub repositories.")
parser.add_argument("--group_url", help="GitHub group URL, e.g. 'https://github.com/SolveCare/'")
parser.add_argument("--repos_to_clone", nargs='*', help="List of repositories to clone, e.g. 'Care.Protocol Care.Labs hyperledger-test-client'")
args = parser.parse_args()

# Get group_url and repos_to_clone either from command line arguments or user input
group_url = args.group_url if args.group_url else input("Enter GitHub group URL (e.g. 'https://github.com/SolveCare/'): ")
repos_to_clone = args.repos_to_clone if args.repos_to_clone else input("Enter repositories to clone separated by space: ").split()

for repo_to_clone in repos_to_clone:
    print(f'> Starting repository {repo_to_clone}')

    # The local path where the repository will be cloned
    local_path = repo_to_clone

    # Clone the repository
    ensure_repo_cloned(group_url, repo_to_clone)

    # Detect and clone the upstream
    upstream_commit_hashes = {}
    upstream_repo_details = get_upstream_repo_details(group_url, repo_to_clone)
    if bool(upstream_repo_details):
        upstream_url = upstream_repo_details.get('svn_url', '')
        print(f"Fork detected from {upstream_repo_details.get('full_name', {})}: {upstream_url}")
        upstream_base_url, upstream_last_part = upstream_url.rsplit('/', 1)
        upstream_base_url += '/' # the base URL needs to end with a "/"
        ensure_repo_cloned(upstream_base_url, upstream_last_part)
        upstream_commit_hashes = load_all_commit_hashes(upstream_last_part)
        num_commits_upstream += len(upstream_commit_hashes)

    print('Starting collecting stats...')

    repo = Repo(local_path)

    unique_repo_commits = [commit for commit in repo.iter_commits() if commit.hexsha not in upstream_commit_hashes]
    num_commits_current = len(list(unique_repo_commits))
    num_commits += num_commits_current

    contributors = [commit.author for commit in unique_repo_commits]
    num_contributors += len(set(contributors))

    num_branches += len([ref for ref in repo.refs if isinstance(ref, git.refs.head.Head)])

    num_tags += len(repo.tags)

    repo_activity_stats[repo_to_clone] = {'num_commits': 0, 'num_lines_added': 0, 'num_lines_deleted': 0, 'num_branches': 0, 'num_tags': 0}

    repo_activity_stats[repo_to_clone]['num_branches'] = len([ref for ref in repo.refs if isinstance(ref, git.refs.head.Head)])
    repo_activity_stats[repo_to_clone]['num_tags'] = len(repo.tags)

    print(f'Simple stats done, starting with contributors (this could take some time with big repos; {num_commits_current} commits in this repo)...')

    for commit in unique_repo_commits:
        author = commit.author.name + ' (' + commit.author.email + ')'

        if author not in author_stats:
            # username = ''
            # username_response = requests.get(f"https://api.github.com/search/users?q={commit.author.email}+in:email")
            # if username_response.status_code == 200:
            #     data = username_response.json()
            #     if data["total_count"] > 0:
            #         username = data["items"][0]["login"]
            #         print(f"GitHub username found: {username}")
            #     else:
            #         print(f"No GitHub user found with email '{commit.author.email}'")
            # else:
            #     print("Error accessing GitHub API to receive username from email")
            # author_stats[author] = {'num_commits': 0, 'num_lines_added': 0, 'num_lines_deleted': 0, 'github_username': username}
            author_stats[author] = {'num_commits': 0, 'num_lines_added': 0, 'num_lines_deleted': 0}

        num_insertions = commit.stats.total['insertions']
        num_deletions = commit.stats.total['deletions']
        if num_insertions == 0 and num_deletions == 0:
            num_empty_commits += 1
        
        author_stats[author]['num_commits'] += 1
        author_stats[author]['num_lines_added'] += num_insertions
        author_stats[author]['num_lines_deleted'] += num_deletions

        repo_activity_stats[repo_to_clone]['num_commits'] += 1
        repo_activity_stats[repo_to_clone]['num_lines_added'] += num_insertions
        repo_activity_stats[repo_to_clone]['num_lines_deleted'] += num_deletions

    print('Contributors loaded, gathering recent usage...')

    for commit in unique_repo_commits:
        # If the commit is older than the cutoff date, skip it
        if commit.committed_date < CUTOFF_TIME_RECENT:
            continue

        author = commit.author.name + ' (' + commit.author.email + ')'

        if author not in author_stats_recent:
            author_stats_recent[author] = {'num_commits': 0, 'num_lines_added': 0, 'num_lines_deleted': 0}

        author_stats_recent[author]['num_commits'] += 1
        author_stats_recent[author]['num_lines_added'] += commit.stats.total['insertions']
        author_stats_recent[author]['num_lines_deleted'] += commit.stats.total['deletions']

print('All data loaded, about to sort...')
sorted_author_stats = sorted(author_stats.items(), key=lambda item: item[1]['num_commits'], reverse=True)
sorted_author_stats_recent = sorted(author_stats_recent.items(), key=lambda item: item[1]['num_commits'], reverse=True)

sorted_repo_activity_stats = sorted(repo_activity_stats.items(), key=lambda item: item[1]['num_commits'], reverse=True)

print('')
print('-----------')
print('| Results |')
print('-----------')
print('')
print('Overview')
print('--------')
print('Number of commits in project:', num_commits)
print('Number of commits from upstream (forked project):', num_commits_upstream)
print('Number of contributors:', num_contributors)
print('Number of branches (Upstream not excluded):', num_branches)
print('Number of tags (Upstream not excluded):', num_tags)
print('')
print(f'Top {NUM_CONTRIBUTORS_PRINTED} Contributors (by number of commits)')
print('--------')
for author, stats in sorted_author_stats[:NUM_CONTRIBUTORS_PRINTED]:
    # author_github_username = f' (Github username: {stats["github_username"]} https://github.com/{stats["github_username"]})' if stats["github_username"] else ''
    # print(f'Author: {author} {stats["github_username"]}{author_github_username}')
    print(f'Author: {author}')
    print(f'Number of commits: {stats["num_commits"]:,}'.replace(',', "'"))
    print(f'Number of lines added: {stats["num_lines_added"]:,}'.replace(',', "'"))
    print(f'Number of lines deleted: {stats["num_lines_deleted"]:,}'.replace(',', "'"))
    print()
cutoff_date_formatted = datetime.fromtimestamp(CUTOFF_TIME_RECENT).strftime('%d.%m.%y')
print(f'Top {NUM_CONTRIBUTORS_PRINTED} Contributors recently (since {cutoff_date_formatted}) (by number of commits):')
print('--------')
for author, stats in sorted_author_stats_recent[:NUM_CONTRIBUTORS_PRINTED]:
    print(f'Author: {author}')
    print(f'Number of commits: {stats["num_commits"]:,}'.replace(',', "'"))
    print(f'Number of lines added: {stats["num_lines_added"]:,}'.replace(',', "'"))
    print(f'Number of lines deleted: {stats["num_lines_deleted"]:,}'.replace(',', "'"))
    print()

print('Top 3 Most Active Repositories')
print('------------------------------')
for repo_name, stats in sorted_repo_activity_stats[:3]:
    print(f'Repository: {repo_name}')
    print(f'Number of commits: {stats["num_commits"]:,}'.replace(',', "'"))
    print(f'Number of lines added: {stats["num_lines_added"]:,}'.replace(',', "'"))
    print(f'Number of lines deleted: {stats["num_lines_deleted"]:,}'.replace(',', "'"))
    print(f'Number of branches: {stats["num_branches"]}')
    print(f'Number of tags: {stats["num_tags"]}')
    print()

if num_empty_commits != 0:
    print(f'Warning, the analysed repositories contain empty commits (nothing added or removed). Total empty commits: {num_empty_commits}')

print('Done')
