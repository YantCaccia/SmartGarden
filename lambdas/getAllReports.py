import os, json, time
from utilities import Utilities

def get_all_reports_keys():
    response = Utilities.s3.list_objects_v2(Bucket='smartgarden-s3-bucket')
    if 'Contents' in response:
        reports = []
        for content in response['Contents']:
            if 'Key' in content:
                reports.append(content["Key"])
        return reports
    return None


def get_all_reports():
    keys = get_all_reports_keys()
    if keys is not None:
        reports = []
        for key in keys:
            response = Utilities.s3.get_object(Bucket='smartgarden-s3-bucket', Key=key)
            reports.append({
                "key": key,
                "bytes": response['Body'].read().decode('utf-8')
            })
        return reports
    return None


def lambda_handler(event, context):
    os.putenv('TZ', 'Europe/Rome')
    time.tzset()
    try:
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(get_all_reports())
        }

    except Exception as e:
        print(f"An error occurred {e}")
        Utilities.logger.exception(e)