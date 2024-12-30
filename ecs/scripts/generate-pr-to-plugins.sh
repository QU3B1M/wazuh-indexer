#!/usr/bin/env bash

set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check if branch name and GitHub token are provided
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 <branch_name> <github_token>"
  exit 1
fi

# Define paths and constants
branch_name=$1
github_token=$2
REPO_PATH=/Users/quebim_wz/Wazuh/forked/test
BASE_BRANCH="master"
CURRENT_PATH=$(pwd)

# Step 1: Install Docker if not installed
if ! command_exists docker; then
    echo "Docker not found, installing..."
    sudo apt-get update
    sudo apt-get install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
fi

# Step 2: Install Docker Compose if not installed
if ! command_exists docker-compose; then
    echo "Docker Compose not found, installing..."
    sudo apt-get update
    sudo apt-get install -y docker-compose
fi

# Step 3: Install GitHub CLI if not installed
if ! command_exists gh; then
    echo "GitHub CLI not found, installing..."
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
    sudo apt-key add /usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    sudo apt update
    sudo apt install -y gh
fi

# Step 4: Fetch base branch
git fetch origin +refs/heads/master:refs/remotes/origin/master

# Extract the ECS module names from the modified files
modified_files=$(git diff --name-only origin/$BASE_BRANCH)
updated_modules=()
for file in $modified_files; do
    if [[ $file == ecs/* ]]; then
        ecs_module=$(echo $file | cut -d'/' -f2)
        if [[ ! " ${updated_modules[*]} " =~ " ${ecs_module} " ]]; then
            updated_modules+=("$ecs_module")
        fi
    fi
done
echo "Updated ECS modules: ${updated_modules[*]}"

# Filter out modules that do not have corresponding JSON files
declare -A module_to_file=(
    [agent]="index-template-agent.json"
    [alerts]="index-template-alerts.json"
    [commands]="index-template-commands.json"
    [states-fim]="index-template-fim.json"
    [states-inventory-hardware]="index-template-hardware.json"
    [states-inventory-hotfixes]="index-template-hotfixes.json"
    [states-inventory-networks]="index-template-networks.json"
    [states-inventory-packages]="index-template-packages.json"
    [states-inventory-ports]="index-template-ports.json"
    [states-inventory-processes]="index-template-processes.json"
    [states-inventory-scheduled-commands]="index-template-scheduled-commands.json"
    [states-inventory-system]="index-template-system.json"
    [states-vulnerabilities]="index-template-vulnerabilities.json"
)

relevant_modules=()
for ecs_module in "${updated_modules[@]}"; do
    if [[ -n "${module_to_file[$ecs_module]}" ]]; then
        relevant_modules+=("$ecs_module")
    fi
done

echo "Relevant ECS modules: ${relevant_modules[*]}"

if [[ ${#relevant_modules[@]} -gt 0 ]]; then
    for ecs_module in "${relevant_modules[@]}"; do
        # Run the ECS generator script for each relevant module
        bash ecs/generator/mapping-generator.sh run "$ecs_module"
        echo "Processed ECS module: $ecs_module"
    done
else
    echo "No relevant modifications detected in ecs/ directory."
    exit 0
fi

# Step 6: Tear down ECS Generator
bash ecs/generator/mapping-generator.sh down
cd $REPO_PATH

# Step 7: Checkout target repository
git clone https://github.com/QU3B1M/wazuh-indexer-plugins.git wazuh-indexer-plugins
cd wazuh-indexer-plugins
git config --global user.email "github-actions@github.com"
git config --global user.name "GitHub Actions"
git pull

# Step 8: Set up authentication with GitHub token
git remote set-url origin https://$github_token@github.com/QU3B1M/wazuh-indexer-plugins.git

# Step 9: Commit and push changes
# Check if branch exists
if git ls-remote --exit-code --heads origin $branch_name >/dev/null 2>&1; then
    echo "branch exists"
    git checkout $branch_name
    git pull origin $branch_name
else
    echo "branch does not exist"
    git checkout -b $branch_name
    git push --set-upstream origin $branch_name
fi

# Map ECS modules to target JSON filenames
for ecs_module in ${relevant_modules[@]}; do
    target_file=${module_to_file[$ecs_module]}
    if [[ -z "$target_file" ]]; then
        echo "No corresponding file for module $ecs_module"
        continue
    fi

    mkdir -p plugins/setup/src/main/resources/
    echo "Copying ECS template for module $ecs_module to $target_file"
    mv "$CURRENT_PATH/ecs/$ecs_module/mappings/v8.11.0/generated/elasticsearch/legacy/template.json" "plugins/setup/src/main/resources/$target_file"
done

git status
git add .
git commit -m "Update ECS templates for modified modules: ${relevant_modules[*]}"
git push

# Step 10: Create or Update Pull Request using gh CLI
echo $github_token | gh auth login --with-token

# Check if PR exists for the branch
existing_pr=$(gh pr list --head $branch_name --json number --jq '.[].number')

if [ -z "$existing_pr" ]; then
  # Create a new PR
  gh pr create \
    --title "Update ECS templates for modified modules: ${relevant_modules[*]}" \
    --body "This PR updates the ECS templates for the following modules: ${relevant_modules[*]}." \
    --base master \
    --head $branch_name
else
  # Update existing PR
  gh pr edit $existing_pr \
    --title "Update ECS templates for modified modules: ${relevant_modules[*]}" \
    --body "This PR updates the ECS templates for the following modules: ${relevant_modules[*]}."
fi

echo "ECS Generator script completed."

rm -r ../wazuh-indexer-plugins
