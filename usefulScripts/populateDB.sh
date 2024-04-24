# Just In Case
alias awslocal="AWS_ACCESS_KEY_ID=test \
                AWS_SECRET_ACCESS_KEY=test \
                AWS_DEFAULT_REGION=${DEFAULT_REGION:-$AWS_DEFAULT_REGION} \
                aws --endpoint-url=http://${LOCALSTACK_HOST:-localhost}:4566"

# Just In Case
region="eu-central-1" 

# DynamoDB
awslocal dynamodb put-item \
    --table-name Pots \
    --item '{
        "PotID": {"S": "0"},
        "temperature": {"S": "18"},
        "humidity": {"S": "25"},
        "light": {"S": "30"},
        "coverStatus": {"S": "open"},
        "latestIrrigation": {"S": "Tue 16 Apr 2024, 18:56"}
      }' \
    --region $region

awslocal dynamodb put-item \
    --table-name Pots \
    --item '{
        "PotID": {"S": "1"},
        "temperature": {"S": "25"},
        "humidity": {"S": "30"},
        "light": {"S": "40"},
        "coverStatus": {"S": "open"},
        "latestIrrigation": {"S": "Mon 14 Apr 2024, 20:01"}
      }' \
    --region $region

awslocal dynamodb put-item \
    --table-name Pots \
    --item '{
        "PotID": {"S": "2"},
        "temperature": {"S": "15"},
        "humidity": {"S": "35"},
        "light": {"S": "45"},
        "coverStatus": {"S": "closed"},
        "latestIrrigation": {"S": "Fri 19 Apr 2024, 15:32"}
      }' \
    --region $region

# S3
awslocal s3 cp "./examples/24 Apr 2024 - 00 28.json" s3://smartgarden-s3-bucket