import os, json, time
from utilities import Utilities

def get_latest_modified_key():
    response = Utilities.s3.list_objects_v2(Bucket='smartgarden-s3-bucket')
    if 'Contents' in response:
        latest_updated = max(response["Contents"], key=lambda x: x.get("LastModified", 0))
        return latest_updated.get("Key", '')
    return None

def get_file_from_key(key: str | None):
    if key is not None:
        response = Utilities.s3.get_object(Bucket='smartgarden-s3-bucket', Key=key)
        return {
            "key": key,
            "bytes": response['Body'].read().decode('utf-8')
        }
    return None

def get_file_from_name(name: str):
    # Just checking if the file exists
    response = Utilities.s3.list_objects_v2(Bucket='smartgarden-s3-bucket')
    if 'Contents' in response:
        for content in response['Contents']:
            if 'Key' in content and content["Key"] == name:
                return get_file_from_key(content["Key"])
    return None

def lambda_handler(event, context):
    os.putenv('TZ', 'Europe/Rome')
    time.tzset()
    try:
        # That's so much Java's Nullable style - I'm sorry! :)
        query_params = event.get('queryStringParameters', None)
        report_name = query_params.get('reportName', None) if query_params is not None else None
        to_be_returned = get_file_from_name(report_name) if report_name is not None else get_file_from_key(get_latest_modified_key())
        
        if to_be_returned is not None:
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps(to_be_returned)
            }
        else:
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({'message': 'File not found'})
            }
          
    except Exception as e:
        print(f"An error occurred {e}")
        raise e