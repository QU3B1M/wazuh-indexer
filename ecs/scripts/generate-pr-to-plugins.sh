#!/usr/bin/env bash

set -e

# Constants
MAPPINGS_SUBPATH="mappings/v8.11.0/generated/elasticsearch/legacy/template.json"
TEMPLATES_PATH="plugins/setup/src/main/resources/"
PLUGINS_REPO="QU3B1M/wazuh-indexer-plugins"
CURRENT_PATH=$(pwd)
BASE_BRANCH=${BASE_BRANCH:-master}
PLUGINS_LOCAL_PATH=${PLUGINS_LOCAL_PATH:-"$CURRENT_PATH"/../wazuh-indexer-plugins}
# Global variables
declare -a relevant_modules
declare -A module_to_file

command_exists() {
    command -v "$1" &> /dev/null
}

validate_dependencies() {
    local required_commands=("docker" "docker-compose" "gh")
    for cmd in "${required_commands[@]}"; do
        if ! command_exists "$cmd"; then
            echo "Error: $cmd is not installed. Please install it and try again."
            exit 1
        fi
    done
}

fetch_and_extract_modules() {
    echo
    echo "---> Fetching and extracting modified ECS modules..."
    git fetch origin +refs/heads/master:refs/remotes/origin/master
    local modified_files
    local updated_modules=()
    modified_files=$(git diff --name-only origin/"$BASE_BRANCH")
    
    for file in $modified_files; do
        if [[ $file == ecs/* ]]; then
            ecs_module=$(echo "$file" | cut -d'/' -f2)
            if [[ ! " ${updated_modules[*]} " =~ ${ecs_module} ]]; then
                updated_modules+=("$ecs_module")
            fi
        fi
    done
    echo "Updated ECS modules: ${updated_modules[*]}"

    # Mapping section
    module_to_file=(
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
}

run_ecs_generator() {
    echo
    echo "---> Running ECS Generator script..."
    if [[ ${#relevant_modules[@]} -gt 0 ]]; then
        for ecs_module in "${relevant_modules[@]}"; do
            bash ecs/generator/mapping-generator.sh run "$ecs_module"
            echo "Processed ECS module: $ecs_module"
            bash ecs/generator/mapping-generator.sh down
        done
    else
        echo "No relevant modifications detected in ecs/ directory."
        exit 0
    fi
}


clone_target_repo() {
    echo
    echo "---> Cloning ${PLUGINS_REPO} repository..."
    if [ ! -d "$PLUGINS_LOCAL_PATH" ]; then
        git clone https://github.com/$PLUGINS_REPO.git "$PLUGINS_LOCAL_PATH"
    fi
    cd "$PLUGINS_LOCAL_PATH"
    git config --global user.email "github-actions@github.com"
    git config --global user.name "GitHub Actions"
    git pull
}

commit_and_push_changes() {
    echo
    echo "---> Committing and pushing changes to ${PLUGINS_REPO} repository..."
    git ls-remote --exit-code --heads origin "$branch_name" >/dev/null 2>&1
    EXIT_CODE=$?

    if [[ $EXIT_CODE == '0' ]]; then
        git checkout "$branch_name"
        git pull origin "$branch_name"
    else
        git checkout -b "$branch_name"
        git push --set-upstream origin "$branch_name"
    fi

    echo "Copying ECS templates to the plugins repository..."
    for ecs_module in "${relevant_modules[@]}"; do
        target_file=${module_to_file[$ecs_module]}
        if [[ -z "$target_file" ]]; then
            continue
        fi

        mkdir -p $TEMPLATES_PATH
        echo "  - Copy template for module '$ecs_module' to '$target_file'"
        cp "$CURRENT_PATH/ecs/$ecs_module/$MAPPINGS_SUBPATH" "$TEMPLATES_PATH/$target_file"
    done

    git status --short

    if ! git diff-index --quiet HEAD --; then
        echo "Changes detected. Committing and pushing to the repository..."
        git add .
        git commit -m "Update ECS templates for modified modules: ${relevant_modules[*]}"
        git push
    else
        echo "Nothing to commit, working tree clean."
        exit 0
    fi
}

create_or_update_pr() {
    echo
    echo "---> Creating or updating Pull Request..."
    gh auth login --with-token
    local existing_pr
    local modules
    local title="Update ECS templates for modified modules: ${modules}"
    local body="This PR updates the ECS templates for the following modules: ${modules}."
    existing_pr=$(gh pr list --head "$branch_name" --json number --jq '.[].number')
    modules=$(IFS=,; echo "${relevant_modules[*]}")

    if [ -z "$existing_pr" ]; then
        gh pr create \
            --title "$title" \
            --body "$body" \
            --base master \
            --head "$branch_name"
    else
        echo "PR already exists: $existing_pr. Updating the PR..."
        gh pr edit "$existing_pr" \
            --title "$title" \
            --body "$body"
    fi
}

usage() {
    echo "Usage: $0 -b <branch_name> -t <GITHUB_TOKEN>"
    echo "  -b <branch_name>    Branch name to create or update the PR."
    echo "  -t [GITHUB_TOKEN]   (Optional) GitHub token to authenticate with GitHub API."
    echo "                      If not provided, the script will use the GITHUB_TOKEN environment variable."
    exit 1
}

main() {
    while getopts ":b:t:" opt; do
        case ${opt} in
            b )
                branch_name=$OPTARG
                ;;
            t )
                GITHUB_TOKEN=$OPTARG
                ;;
            \? )
                usage
                ;;
            : )
                echo "Invalid option: $OPTARG requires an argument" 1>&2
                usage
                ;;
        esac
    done
    if [ -z "$branch_name" ] || [ -z "$GITHUB_TOKEN" ]; then
        usage
    fi

    validate_dependencies
    fetch_and_extract_modules
    run_ecs_generator # Exit if no changes on relevant modules.
    clone_target_repo
    commit_and_push_changes # Exit if no changes detected.
    create_or_update_pr
}

main "$@"
