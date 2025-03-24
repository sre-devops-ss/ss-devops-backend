#!/bin/bash
echo "Processing folders..."
for folder in $CHANGED_FOLDERS; do
  CHANGED_FOLDERS=$(echo "$CHANGED_FOLDERS" | grep -v '^RESOURCE-SETUP$')
  echo "Processing folder: $folder"
  if [ -f "$folder/template.yaml" ]; then
    echo "Found template.yaml in $folder. Running SAM build and deploy..."
    TemplatePath="$folder/template.yaml"
    sam build -t $TemplatePath
    SAM_CLI_POLL_DELAY=5 sam deploy --stack-name "ss-devops-backend-sam-stack" --s3-bucket $Bucket --s3-prefix ss-devops-backend --capabilities CAPABILITY_IAM
  else
    echo "No template.yaml found in $folder. Skipping."
  fi
done