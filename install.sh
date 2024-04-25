clear

# Install jq
# sudo apt-get install jq -y

# Sourcing .env variables
set -a
source .env
set +a


# Setup awslocal
alias awslocal="AWS_ACCESS_KEY_ID=test \
                AWS_SECRET_ACCESS_KEY=test \
                AWS_DEFAULT_REGION=${DEFAULT_REGION:-$AWS_DEFAULT_REGION} \
                aws --endpoint-url=http://${LOCALSTACK_HOST:-localhost}:4566"

region=$(awslocal configure get region)
echo "Default AWS region: $region"

# Create S3
echo "\nCreating S3 bucket"
awslocal s3api create-bucket \
    --bucket smartgarden-s3-bucket

# Create a DynamoDB table
echo "\nCreating DynamoDB table"
awslocal dynamodb create-table \
    --table-name Pots \
    --attribute-definitions AttributeName=PotID,AttributeType=S \
    --key-schema AttributeName=PotID,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1 \
    --region $region \
    --no-cli-pager

# Create SQS
echo "\nCreating SQS queue"
WateringQueueCreationOutput=$(awslocal sqs create-queue --queue-name WateringQueue --region $region)
WateringQueueURL=$(echo "$WateringQueueCreationOutput" | jq -r '.QueueUrl')
WateringQueueARN=$(awslocal sqs get-queue-attributes \
    --queue-url $WateringQueueURL \
    --attribute-name QueueArn | jq -r '.Attributes.QueueArn')
echo $WateringQueueARN
echo "WateringQueueUrl: $WateringQueueURL"

# Create Kinesis stream
echo "\nCreating Kinesis stream"
awslocal kinesis create-stream --stream-name SensorsToLambda --shard-count 1 --region $region
KinesisStreamARN=$(awslocal kinesis describe-stream --stream-name SensorsToLambda --region $region | jq -r '.StreamDescription.StreamARN')
echo $KinesisStreamARN

# Create Role for Lambda execution
Role=$(awslocal iam create-role --role-name LambdaAndKinesisRole --assume-role-policy-document file://./roles/lambda_role.json)
RoleARN=$(echo "$Role" | jq -r '.Role.Arn')
echo "\n\nROLE: $Role \n\nROLE ARN: $RoleARN"

# Attach Role Policy to Role
awslocal iam attach-role-policy --role-name LambdaAndKinesisRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaKinesisExecutionRole

# Lambdas
echo "\nCreating Lambdas"

mkdir ./tmpZips

#--- CheckDataFromDevice ---#
CheckDataFromDeviceFunctionName=checkDataFromDevice

# Zip src
zip -j ./tmpZips/$CheckDataFromDeviceFunctionName.zip ./lambdas/$CheckDataFromDeviceFunctionName.py ./lambdas/utilities.py

# Create lambda
awslocal lambda create-function --function-name $CheckDataFromDeviceFunctionName \
    --zip-file fileb://./tmpZips/$CheckDataFromDeviceFunctionName.zip \
    --handler $CheckDataFromDeviceFunctionName.lambda_handler \
    --runtime python3.12 \
    --role $RoleARN \
    --no-cli-pager

# Create Event-Source Mapping for checkDataFromDevice
awslocal lambda create-event-source-mapping \
    --function-name $CheckDataFromDeviceFunctionName \
    --event-source $KinesisStreamARN \
    --batch-size 5 \
    --starting-position LATEST \
    --no-cli-pager


#--- ActuateNow ---#
ActuateNowFunctionName=actuateNow

# Zip src
zip -j ./tmpZips/$ActuateNowFunctionName.zip ./lambdas/$ActuateNowFunctionName.py ./lambdas/utilities.py

# Create lambda
awslocal lambda create-function --function-name $ActuateNowFunctionName \
    --zip-file fileb://./tmpZips/$ActuateNowFunctionName.zip \
    --handler $ActuateNowFunctionName.lambda_handler \
    --runtime python3.12 \
    --role $RoleARN \
    --environment "Variables={TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN,TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID}" \
    --no-cli-pager

# Create Event-Source Mapping for actuateNow
awslocal lambda create-event-source-mapping \
    --function-name $ActuateNowFunctionName \
    --event-source $WateringQueueARN \
    --batch-size 5 \
    --starting-position LATEST \
    --no-cli-pager


#--- GetActuatorsStatus ---#
GetActuatorsStatusFunctionName=getActuatorsStatus

# Zip src
zip -j ./tmpZips/$GetActuatorsStatusFunctionName.zip ./lambdas/$GetActuatorsStatusFunctionName.py ./lambdas/utilities.py

# Create lambda
awslocal lambda create-function --function-name $GetActuatorsStatusFunctionName \
    --zip-file fileb://./tmpZips/$GetActuatorsStatusFunctionName.zip \
    --handler $GetActuatorsStatusFunctionName.lambda_handler \
    --runtime python3.12 \
    --role $RoleARN \
    --no-cli-pager


#--- GetSensorData ---#
GetSensorDataFunctionName=getLatestSensorData

# Zip src
zip -j ./tmpZips/$GetSensorDataFunctionName.zip ./lambdas/$GetSensorDataFunctionName.py ./lambdas/utilities.py

# Create lambda
awslocal lambda create-function --function-name $GetSensorDataFunctionName \
    --zip-file fileb://./tmpZips/$GetSensorDataFunctionName.zip \
    --handler $GetSensorDataFunctionName.lambda_handler \
    --runtime python3.12 \
    --role $RoleARN \
    --no-cli-pager


#--- CreateReport ---#
CreateReportFunctionName=createReport

# Zip src
zip -j ./tmpZips/$CreateReportFunctionName.zip ./lambdas/$CreateReportFunctionName.py ./lambdas/utilities.py

# Create lambda
awslocal lambda create-function --function-name $CreateReportFunctionName \
    --zip-file fileb://./tmpZips/$CreateReportFunctionName.zip \
    --handler $CreateReportFunctionName.lambda_handler \
    --runtime python3.12 \
    --role $RoleARN \
    --environment "Variables={TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN,TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID}" \
    --no-cli-pager


#--- DownloadReport ---#
DownloadReportFunctionName=getReport

# Zip src
zip -j ./tmpZips/$DownloadReportFunctionName.zip ./lambdas/$DownloadReportFunctionName.py ./lambdas/utilities.py

# Create lambda
awslocal lambda create-function --function-name $DownloadReportFunctionName \
    --zip-file fileb://./tmpZips/$DownloadReportFunctionName.zip \
    --handler $DownloadReportFunctionName.lambda_handler \
    --runtime python3.12 \
    --role $RoleARN \
    --no-cli-pager

#--- DownloadAllReports ---#
DownloadAllReportsFunctionName=getAllReports

# Zip src
zip -j ./tmpZips/$DownloadAllReportsFunctionName.zip ./lambdas/$DownloadAllReportsFunctionName.py ./lambdas/utilities.py

# Create lambda
awslocal lambda create-function --function-name $DownloadAllReportsFunctionName \
    --zip-file fileb://./tmpZips/$DownloadAllReportsFunctionName.zip \
    --handler $DownloadAllReportsFunctionName.lambda_handler \
    --runtime python3.12 \
    --role $RoleARN \
    --no-cli-pager


# EventBridge Rule
echo "\nCreating EventBridge Rule"
awslocal events put-rule \
    --name scheduled-generate-report \
    --schedule-expression 'cron(00 10 * * ? *)' \
    --region us-east-1

awslocal lambda add-permission \
    --function-name $CreateReportFunctionName \
    --statement-id scheduled-generate-report-event \
    --action 'lambda:InvokeFunction' \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:us-east-1:000000000000:rule/scheduled-generate-report

awslocal events put-targets \
    --rule scheduled-generate-report \
    --targets file://targets/targets.json \
    --region us-east-1


# Create API Gateway
echo "\nCreating API Gateway"
output_api1=$(awslocal apigateway create-rest-api --name 'SmartGarden API Gateway' --region us-east-1)
api_id1=$(echo $output_api1 | jq -r '.id')

output_parent1=$(awslocal apigateway get-resources --rest-api-id $api_id1 --region us-east-1)
parent_id1=$(echo $output_parent1 | jq -r '.items[0].id')

# -- ActualStatusEndpoint -- #
# Create ActualStatusEndpoint
output_ActualStatusEndpoint=$(awslocal apigateway create-resource --rest-api-id $api_id1 --parent-id $parent_id1 --path-part latestSensorData --region us-east-1)
ActualStatusEndpoint_id=$(echo $output_ActualStatusEndpoint | jq -r '.id')

# Putting methods
output_get_ActualStatusEndpoint=$(awslocal apigateway put-method --rest-api-id $api_id1 --resource-id $ActualStatusEndpoint_id --http-method GET --authorization-type "NONE" --region us-east-1)

# Creating integration
awslocal apigateway put-integration --rest-api-id $api_id1 --resource-id $ActualStatusEndpoint_id --http-method GET --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/$GetSensorDataFunctionName/invocations" --passthrough-behavior WHEN_NO_MATCH


# -- LatestActuatorEndpoint -- #
# Create LatestActuatorEndpoint
output_LatestActuatorEndpoint=$(awslocal apigateway create-resource --rest-api-id $api_id1 --parent-id $parent_id1 --path-part actuatorStatus --region us-east-1)
LatestActuatorEndpoint_id=$(echo $output_LatestActuatorEndpoint | jq -r '.id')

# Putting methods
output_get_LatestActuatorEndpoint=$(awslocal apigateway put-method --rest-api-id $api_id1 --resource-id $LatestActuatorEndpoint_id --http-method GET --authorization-type "NONE" --region us-east-1)

# Creating integration
awslocal apigateway put-integration --rest-api-id $api_id1 --resource-id $LatestActuatorEndpoint_id --http-method GET --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/$GetActuatorsStatusFunctionName/invocations" --passthrough-behavior WHEN_NO_MATCH


# -- ActuateNowEndpoint -- #
# Create ActuateNowEndpoint
output_ActuateNowEndpoint=$(awslocal apigateway create-resource --rest-api-id $api_id1 --parent-id $parent_id1 --path-part actuateNow --region us-east-1)
ActuateNowEndpoint_id=$(echo $output_ActuateNowEndpoint | jq -r '.id')

# Putting methods
output_get_ActuateNowEndpoint=$(awslocal apigateway put-method --rest-api-id $api_id1 --resource-id $ActuateNowEndpoint_id --http-method GET --authorization-type "NONE" --region us-east-1)

# Creating integration
awslocal apigateway put-integration --rest-api-id $api_id1 --resource-id $ActuateNowEndpoint_id --http-method GET --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/$ActuateNowFunctionName/invocations" --passthrough-behavior WHEN_NO_MATCH


# -- CreateReportEndpoint -- #
# Create CreateReportEndpoint
output_CreateReportEndpoint=$(awslocal apigateway create-resource --rest-api-id $api_id1 --parent-id $parent_id1 --path-part generateReport --region us-east-1)
CreateReportEndpoint_id=$(echo $output_CreateReportEndpoint | jq -r '.id')

# Putting methods
output_get_CreateReportEndpoint=$(awslocal apigateway put-method --rest-api-id $api_id1 --resource-id $CreateReportEndpoint_id --http-method GET --authorization-type "NONE" --region us-east-1)

# Creating integration
awslocal apigateway put-integration --rest-api-id $api_id1 --resource-id $CreateReportEndpoint_id --http-method GET --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/$CreateReportFunctionName/invocations" --passthrough-behavior WHEN_NO_MATCH


# -- DownloadReportEndpoint -- #
# Create DownloadReportEndpoint
output_DownloadReportEndpoint=$(awslocal apigateway create-resource --rest-api-id $api_id1 --parent-id $parent_id1 --path-part downloadReport --region us-east-1)
DownloadReportEndpoint_id=$(echo $output_DownloadReportEndpoint | jq -r '.id')

# Putting methods
output_get_DownloadReportEndpoint=$(awslocal apigateway put-method --rest-api-id $api_id1 --resource-id $DownloadReportEndpoint_id --http-method GET --authorization-type "NONE" --region us-east-1)

# Creating integration
awslocal apigateway put-integration --rest-api-id $api_id1 --resource-id $DownloadReportEndpoint_id --http-method GET --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/$DownloadReportFunctionName/invocations" --passthrough-behavior WHEN_NO_MATCH

## -- DownloadAllReportsEndpoint -- #
# Create DownloadAllReportsEndpoint
output_DownloadAllReportsEndpoint=$(awslocal apigateway create-resource --rest-api-id $api_id1 --parent-id $parent_id1 --path-part downloadAllReports --region us-east-1)
DownloadAllReportsEndpoint_id=$(echo $output_DownloadAllReportsEndpoint | jq -r '.id')

# Putting methods
output_get_DownloadAllReportsEndpoint=$(awslocal apigateway put-method --rest-api-id $api_id1 --resource-id $DownloadAllReportsEndpoint_id --http-method GET --authorization-type "NONE" --region us-east-1)

# Creating integration
awslocal apigateway put-integration --rest-api-id $api_id1 --resource-id $DownloadAllReportsEndpoint_id --http-method GET --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/$DownloadAllReportsFunctionName/invocations" --passthrough-behavior WHEN_NO_MATCH

AWS_GATEWAY_URL="http://localhost:4566/restapis/$api_id1/test/_user_request_/"
echo "\n\nAPI Gateway URL: $AWS_GATEWAY_URL\n\n"
echo "\nAWS_GATEWAY_URL=$AWS_GATEWAY_URL" >> ./.env


# Remove tmp files
rm -r ./tmpZips/*
rm -f ./tmpZips/.DS_Store
rmdir ./tmpZips

# Populate DB
echo "\nPopulating DB\n"
chmod +x ./usefulScripts/populateDB.sh
./usefulScripts/populateDB.sh