import base64, json, os, time
from datetime import datetime, timedelta
from dataclasses import dataclass
from utilities import Utilities

@dataclass
class sensorData():
    potID: int
    sensorType: str
    readValue: int

from_sensor_to_actuator: dict[str, str] = {
    'light': 'cover',
    'temperature': 'cover',
    'humidity': 'irrigator'
}

from_actuator_to_state: dict[str, str] = {
    'cover': 'coverStatus',
    'irrigator': 'latestIrrigation'
}

def actuator_activation_is_needed(item: dict, actuator: str, statusAfterUpdate: str):
    if actuator == 'cover':
        return item[from_actuator_to_state[actuator]]['S'] != statusAfterUpdate
    elif actuator == 'irrigator':
        latestIrrigation = datetime.strptime(item[from_actuator_to_state[actuator]]['S'], '%a %d %b %Y, %H:%M')
        return datetime.now() - latestIrrigation > timedelta(minutes=30)
        
    
def update_item(potID: int, attribute: str, value: int):
    return Utilities.dynamodb.update_item(
    TableName='Pots',
    Key={
        'PotID': {'S': str(potID)}
    },
    UpdateExpression=f"set {attribute} = :r",
    ExpressionAttributeValues={
        ':r': {'S': str(value)},
    },
    ReturnValues="UPDATED_NEW"
)

def create_sqsentry(potID: int, actuator: str, statusAfterUpdate: str = ''):
    # Generate a message body
    message_body = {
        'potID': str(potID),
        'actuatorToTrigger': actuator,
        'actuatorStatusAfterUpdate': statusAfterUpdate
    }

    # Send the message to the SQS queue
    return Utilities.queue.send_message(
        MessageBody=json.dumps(message_body)
    )

def activate_actuator(pot: int, actuator: str, statusAfterUpdate: str = ''):
    # Check if the actuator is already in the desired state
    response = Utilities.dynamodb.get_item(
        TableName='Pots',
        Key={
            'PotID': {'S': str(pot)}
        }
    )    
    if actuator_activation_is_needed(response['Item'], actuator, statusAfterUpdate):
        # Create SQS entry
        return create_sqsentry(pot, actuator, statusAfterUpdate)

def check_params(data: sensorData):
    update_item(data.potID, data.sensorType, data.readValue)
    
    if data.sensorType == 'light':
        if int(data.readValue) > 50:
            activate_actuator(data.potID, from_sensor_to_actuator.get(data.sensorType, ''), 'close')
        elif int(data.readValue) < 20:
            activate_actuator(data.potID, from_sensor_to_actuator.get(data.sensorType, ''), 'open')
    elif data.sensorType == 'humidity':
        if int(data.readValue) < 60:
            activate_actuator(data.potID, from_sensor_to_actuator.get(data.sensorType, ''))
    elif data.sensorType == 'temperature':
        if int(data.readValue) > 25:
            activate_actuator(data.potID, from_sensor_to_actuator.get(data.sensorType, ''), 'close')
        elif int(data.readValue) < 15:
            activate_actuator(data.potID, from_sensor_to_actuator.get(data.sensorType, ''), 'open')
    else:
        raise Exception('SensorType not recognized')


def lambda_handler(event, context):
    os.putenv('TZ', 'Europe/Rome')
    time.tzset()

    for record in event['Records']:
        try:
            print(f"Processed Kinesis Event - EventID: {record['eventID']}")
            record_data = base64.b64decode(record['kinesis']['data']).decode('utf-8')
            check_params(sensorData(**json.loads(record_data)))
        
        except Exception as e:
            print(f"An error occurred {e}")
            Utilities.logger.exception(e)
            return
    print(f"Successfully processed {len(event['Records'])} records.")
    return
