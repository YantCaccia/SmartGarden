# Just In Case
alias awslocal="AWS_ACCESS_KEY_ID=test \
                AWS_SECRET_ACCESS_KEY=test \
                AWS_DEFAULT_REGION=${DEFAULT_REGION:-$AWS_DEFAULT_REGION} \
                aws --endpoint-url=http://${LOCALSTACK_HOST:-localhost}:4566"

# Just In Case
region="eu-central-1"
echo $region

# Function to generate a random value between a range
random_value() {
    min=10
    max=90
    echo $(($min + $RANDOM % ($max - $min + 1)))
}

# Function to generate a random potID between 0 and 2
random_potID() {
    echo $(($RANDOM % 3))
}

random_sensorType() {
    sensorTypes=("light" "temperature" "humidity")
    echo ${sensorTypes[$RANDOM % 3]}
}

# Function to generate a random record and put it into Kinesis stream
put_record() {
    potID=$(random_potID)
    sensorType=$(random_sensorType)
    readValue=$(random_value)
    data="{\"potID\": \"$potID\", \"sensorType\": \"$sensorType\", \"readValue\": \"$readValue\"}"
    awslocal kinesis put-record --stream-name SensorsToLambda --partition-key 1 --data "$data" --region $region --cli-binary-format raw-in-base64-out
}

# Main loop to continuously generate and put records into Kinesis stream
while true; do
    put_record
    sleep 1
done
