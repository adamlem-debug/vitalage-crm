#!/bin/bash
set -euo pipefail

cd ~
echo "Setting up Bench..."
pip install frappe-bench
bench -v init frappe-bench --skip-assets --skip-redis-config-generation --python "$(which python)" --frappe-branch version-16
cd ./frappe-bench

echo "Getting CRM from the checked-out fork..."
bench get-app --skip-assets crm "${GITHUB_WORKSPACE}"

echo "Generating POT file..."
bench generate-pot-file --app crm

cd ./apps/crm
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git config user.name "github-actions[bot]"

git add crm/locale/main.pot
if git diff --cached --quiet; then
  echo "No changes to POT file; nothing to commit."
  exit 0
fi

echo "Preparing a branch in our fork..."
isodate=$(date -u +"%Y-%m-%d")
branch_name="pot_${BASE_BRANCH}_${isodate}_${GITHUB_RUN_ID}"
git checkout -b "${branch_name}"
git commit -m "chore: update POT file"

# The bench get-app checkout may point to a local path. Always push to our fork.
git remote set-url origin "https://github.com/${GITHUB_REPOSITORY}.git"
gh auth setup-git
git push -u origin "${branch_name}"

echo "Creating a PR in our fork..."
gh pr create --fill --base "${BASE_BRANCH}" --head "${branch_name}" -R "${GITHUB_REPOSITORY}"
