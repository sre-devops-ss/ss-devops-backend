#!/bin/bash
echo "Processing folders..."
CHANGED_FOLDERS=$(echo "$CHANGED_FOLDERS" | grep -v '^RESOURCE-SETUP$')
for folder in $CHANGED_FOLDERS; do
  echo "Processing folder: $folder"
  if [ -f "$folder/template.yaml" ]; then
    echo "Found template.yaml in $folder. Running SAM build and deploy..."
    TemplatePath="$folder/template.yaml"
    sam build -t $TemplatePath
    SAM_CLI_POLL_DELAY=5 sam deploy --stack-name "$folder-sam-stack" --s3-bucket $Bucket --s3-prefix $folder-sam-stack --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --parameter-overrides Environment=$Environment
  else
    echo "No template.yaml found in $folder. Skipping."
  fi

    if [ -f "$folder/domain.yaml" ]; then
      echo "Found domain.yaml in $folder. Running SAM build and deploy..."
      DomainTemplatePath="$folder/domain.yaml"
      sam build -t $DomainTemplatePath
      SAM_CLI_POLL_DELAY=5 sam deploy --stack-name "$folder-domain-sam-stack" --s3-bucket $Bucket --s3-prefix $folder-domain-sam-stack --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --parameter-overrides Environment=$Environment
    else
      echo "No domain.yaml found in $folder. Skipping."
    fi

done