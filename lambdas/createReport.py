import os, json, time
from datetime import datetime
from utilities import Utilities


TELEGRAM_URL = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
TELEGRAM_CHAT_ID = f"{os.environ['TELEGRAM_CHAT_ID']}"


def send_telegram_message(report_name: str):
    payload = {
        "text": f'Successfully generted report {report_name}. You can download it from the S3 bucket.',
        "chat_id": TELEGRAM_CHAT_ID
    }
    Utilities.http.request('POST', TELEGRAM_URL, body=json.dumps(payload), headers={'Content-Type': 'application/json'})
    return


def report_to_s3(body: list[dict]):
    to_upload: dict = {pot['PotID']: pot for pot in body}
    to_upload['created_at'] = str(
        datetime.now().strftime('%a %d %b %Y, %H:%M'))
    report_key = f'{datetime.now().strftime("%d %b %Y - %H:%M")}.json'
    Utilities.s3.put_object(Bucket='smartgarden-s3-bucket', Key=report_key, Body=json.dumps(to_upload))
    return report_key


def get_data():
    # Get all items from the table
    response = Utilities.dynamodb.scan(TableName='Pots')

    to_be_returned: list[dict] = []

    # Iterate over the items
    for item in response['Items']:
        if 'PotID' in item:
            # Get the item
            pot = {key: value['S'] for key, value in item.items()}  # type: ignore
            to_be_returned.append(pot)

    return to_be_returned


def lambda_handler(event, context):
    os.putenv('TZ', 'Europe/Rome')
    time.tzset()
    try:
        all_data = get_data()
        report_key = report_to_s3(all_data)
        if event.get('httpMethod', None) is None:
            # Lambda not invoked by API Gateway => not invoked through the Bot
            send_telegram_message(report_key)
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(all_data)
        }

    except Exception as e:
        print(f"An error occurred {e}")
        raise e
