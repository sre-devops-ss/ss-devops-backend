#!/bin/bash

echo "Processing folder(s)..."

if [ $# -eq 0 ]; then
  echo "No folders passed to script."
  exit 1
fi

for folder in "$@"; do
  echo "Processing folder from script: $folder"
  ls -la $folder
  ls -la
  pwd
  if [ -f "$folder/template.yaml" ]; then
    echo "Found template.yaml in $folder. Running SAM build and deploy..."
    TemplatePath="$folder/template.yaml"
    sam build -t "$TemplatePath"
    SAM_CLI_POLL_DELAY=5 sam deploy \
      --stack-name "$(basename $folder)-sam-stack" \
      --s3-bucket "$Bucket" \
      --s3-prefix "$(basename $folder)-s3-sam-stack" \
      --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
      --parameter-overrides Environment="$Environment"
  else
    echo "No template.yaml found in $folder. Skipping."
  fi

  if [ -f "$folder/domain.yaml" ]; then
    echo "Found domain.yaml in $folder. Running SAM build and deploy..."
    DomainTemplatePath="$folder/domain.yaml"

    sam build -t "$DomainTemplatePath" 2> /tmp/build_error.log || {
      echo "Build failed for $DomainTemplatePath:"
      cat /tmp/build_error.log
    }

    SAM_CLI_POLL_DELAY=5 sam deploy \
      --stack-name "$(basename $folder)-domain-sam-stack" \
      --s3-bucket "$Bucket" \
      --s3-prefix "$(basename $folder)-s3-domain-sam-stack" \
      --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
      --parameter-overrides Environment="$Environment" \
      2> /tmp/deploy_error.log || {
        echo "Deploy failed for $DomainTemplatePath:"
        cat /tmp/deploy_error.log
      }

  else
    echo "No domain.yaml found in $folder. Skipping."
  fi
done
