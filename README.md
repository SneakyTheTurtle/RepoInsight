# RepoInsight
This is a command line tool that provides statistical insight into one or more GitHub repositories. The tool gathers data on commits, contributors, branches, and tags. It also provides detailed contributor statistics, including the number of commits, lines added, and lines deleted. The tool analyzes both overall and recent contributions and checks for empty commits.

## Setup
The tool requires Python to be installed on your machine. It uses the GitPython and requests libraries. If these are not installed, you can install them using pip:

```
pip install gitpython requests
```

To use the tool, you need to download the repoInsight.py script to your local machine.

## Usage
You can run the tool from the command line as follows:

```
python repoInsight.py --group_url <group_url> --repos_to_clone <repo_1> <repo_2> ...
```

Here, <group_url> is the URL of the GitHub group (e.g., 'https://github.com/SolveCare/') and <repo_1> <repo_2> ... is a space-separated list of repositories that you want to clone and analyze.

If you don't provide the --group_url and --repos_to_clone arguments, the script will prompt you to enter them manually.

## Output
The tool outputs the gathered statistics to the console. It provides an overview of the total number of commits, contributors, branches, and tags across all analyzed repositories. It also lists the top contributors (by number of commits) both overall and recently (within the last three months). Additionally, it presents the top three most active repositories based on the number of commits. If there are any empty commits (commits that added or removed nothing), the tool will alert you.