import json, os, time
from datetime import datetime
from utilities import Utilities

TELEGRAM_URL = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
TELEGRAM_CHAT_ID = f"{os.environ['TELEGRAM_CHAT_ID']}"

def send_telegram_message(pot: str, actuator: str, new_status: str):
    text: str = f'Successfully actuated the {actuator} of the pot {pot}.'
    if actuator == 'cover':
        text += f' Its new status is: {new_status}'
    payload = {
        "text": text,
        "chat_id": TELEGRAM_CHAT_ID
    }
    Utilities.http.request('POST', TELEGRAM_URL, body=json.dumps(payload), headers={'Content-Type': 'application/json'})
    return

from_actuator_to_state: dict[str, dict[str, str]] = {
    'cover': {
        'light': '40',
        'temperature': '20'},
    'irrigator': {
        'humidity': '30'
    }
}

def compute_new_values(actual_state_dict: dict, actuator: str, actuatorStatusAfterUpdate: str):
    if actuator == 'cover':
        actual_state_dict['light'] = from_actuator_to_state[actuator]['light']
        actual_state_dict['temperature'] = from_actuator_to_state[actuator]['temperature']
        actual_state_dict['coverStatus'] = actuatorStatusAfterUpdate
    elif actuator == 'irrigator':
        actual_state_dict['humidity'] = from_actuator_to_state[actuator]['humidity']
        actual_state_dict['latestIrrigation'] = datetime.now().strftime('%a %d %b %Y, %H:%M')


def actuate_actuator(potID: str, actuator: str, actuatorStatusAfterUpdate: str):

    # Get the current state of the pot from the DynamoDB
    actual_state = Utilities.dynamodb.get_item(
        TableName='Pots',
        Key={
            'PotID': {'S': str(potID)}
        }
    )
    
    actual_state_dict = {key: value['S'] for key, value in actual_state['Item'].items()} # type: ignore
    
    # Im actuating the actuator (fake)
    compute_new_values(actual_state_dict, actuator, actuatorStatusAfterUpdate)
    
    # Updating the state of the pot in the DynamoDB
    Utilities.dynamodb.update_item(
        TableName='Pots',
        Key={
            'PotID': {'S': str(potID)}
        },
        UpdateExpression="set light = :l, temperature = :t, humidity = :h, coverStatus = :c, latestIrrigation = :i",
        ExpressionAttributeValues={
            ':l': {'S': str(actual_state_dict.get('light', 'N/A'))},
            ':t': {'S': str(actual_state_dict.get('temperature', 'N/A'))},
            ':h': {'S': str(actual_state_dict.get('humidity', 'N/A'))},
            ':c': {'S': actual_state_dict.get('coverStatus', 'N/A')},
            ':i': {'S': actual_state_dict.get('latestIrrigation', 'N/A')}
        }
    )

def lambda_handler(event, context):
    os.putenv('TZ', 'Europe/Rome')
    time.tzset()

    try:
        if event.get('Records', None) is not None and len(event['Records']) > 0:
            # Message from SQS queue
            for record in event['Records']:
                    print(f"Processed Record: {record}")
                    
                    # Receive a message from the SQS queue
                    message = json.loads(record['body'])
                    actuate_actuator(message['potID'], message['actuatorToTrigger'], message['actuatorStatusAfterUpdate'])
                    
                    # Send message through Telegram
                    send_telegram_message(message['potID'], message['actuatorToTrigger'], message['actuatorStatusAfterUpdate'])
        else:
            # Message from the API Gateway
            potID = event['queryStringParameters']['potid']
            actuatorToTrigger = event['queryStringParameters']['actuator']
            actuatorStatusAfterUpdate = event['queryStringParameters']['statusAfterUpdate']
            actuate_actuator(potID, actuatorToTrigger, actuatorStatusAfterUpdate)
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps(f'Successfully actuated the {actuatorToTrigger} of the pot {potID}')
            }
    except Exception as e:
                print(f"An error occurred {e}")
                Utilities.logger.exception(e)