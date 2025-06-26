#!/bin/bash
echo "Processing folders..."
CHANGED_FOLDERS=$(echo "$CHANGED_FOLDERS" | grep -v '^RESOURCE-SETUP$')
for folder in $CHANGED_FOLDERS; do
  echo "Processing folder: $folder"
  
  if [ -f "$folder/template.yaml" ]; then
    echo "Found template.yaml in $folder. Running SAM build and deploy..."
    TemplatePath="$folder/template.yaml"
    sam build -t "$TemplatePath"
    SAM_CLI_POLL_DELAY=5 sam deploy \
      --stack-name "$folder-sam-stack" \
      --s3-bucket "$Bucket" \
      --s3-prefix "$folder-s3-sam-stack" \
      --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
      --parameter-overrides Environment="$Environment"
  else
    echo "No template.yaml found in $folder. Skipping."
  fi

  if [ -f "$folder/domain.yaml" ]; then
    echo "Found domain.yaml in $folder. Running SAM build and deploy..."
    DomainTemplatePath="$folder/domain.yaml"

    # Run SAM build with error capture
    sam build -t "$DomainTemplatePath" 2> /tmp/build_error.log || {
      echo "Build failed for $DomainTemplatePath:"
      cat /tmp/build_error.log
    }

    # Run SAM deploy with error capture
    SAM_CLI_POLL_DELAY=5 sam deploy \
      --stack-name "$folder-domain-sam-stack" \
      --s3-bucket "$Bucket" \
      --s3-prefix "$folder-s3-domain-sam-stack" \
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
