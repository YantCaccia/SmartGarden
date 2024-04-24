import json
from utilities import Utilities

def get_sensor_data():
    # Get all items from the table
    response = Utilities.dynamodb.scan(TableName='Pots')
    
    to_be_returned = []
    
    # Iterate over the items
    for item in response['Items']:
        if 'PotID' in item:
            # Get the item
            pot = {key: value['S'] for key, value in item.items() if key in ['PotID', 'light', 'humidity', 'temperature']} # type: ignore
            to_be_returned.append(pot)
    
    return to_be_returned

def lambda_handler(event, context):
    try:    
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(get_sensor_data())
        }
          
    except Exception as e:
        print(f"An error occurred {e}")
        raise e