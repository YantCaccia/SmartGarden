import urllib3, os, boto3, logging


class Utilities:
    http = urllib3.PoolManager()
    endpoint_url = f"http://{os.environ['LOCALSTACK_HOSTNAME']}:{os.environ['EDGE_PORT']}"
    dynamodb = boto3.client('dynamodb', endpoint_url=endpoint_url, region_name='eu-central-1')
    sqs = boto3.resource('sqs', endpoint_url=endpoint_url, region_name='eu-central-1')
    queue = sqs.get_queue_by_name(QueueName='WateringQueue')
    s3 = boto3.client('s3', endpoint_url=endpoint_url, region_name='eu-central-1')
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)