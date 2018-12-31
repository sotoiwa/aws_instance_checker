# -*- coding: utf-8 -*-
import datetime
import os
import json
import pprint

import boto3
import pytz
import requests

SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']
SLACK_CHANNEL = os.environ['SLACK_CHANNEL']


def get_instances():
    """boto3を使って全てのリージョンで起動しているEC2インスタンスを取得する

    :return: instances
    """

    # 全リージョンを取得
    client = boto3.client('ec2')
    regions = client.describe_regions()['Regions']
    
    instances = []

    # 各リージョン毎に繰り返し
    for region in regions:
        client = boto3.client('ec2', region_name=region['RegionName'])
    
        response = client.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': [
                        'running',
                    ]
                },
            ]
        )

        reservations = response['Reservations']

        if not reservations:
            continue

        for reservation in reservations:
            instance = dict()
            instance['id'] = reservation['Instances'][0]['InstanceId']
            tags = reservation['Instances'][0]['Tags']
            instance['name'] = 'null'
            for tag in tags:
                if tag['Key'] == 'Name':
                    instance['name'] = tag['Value']
            instance['type'] = reservation['Instances'][0]['InstanceType']
            instance['region'] = region['RegionName']
            instances.append(instance)

    return instances


def build_message(instances):
    """SlackにPOSTするメッセージボディを作成する

    :param instances:
    :return: message
    """

    if not instances:
        return None

    now = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))

    text = '{}現在稼働しているEC2インスタンス一覧'.format(now.strftime('%Y年%m月%d日%H時%M分'))
    atachements_text = ''
    for instance in instances:
        atachements_text += 'name: {}, type: {}, id: {}, region: {}\n'.format(
            instance['name'], instance['type'], instance['id'], instance['region'])

    atachements = {'text': atachements_text, 'color': 'red'}

    message = {
        'text': text,
        'channel': SLACK_CHANNEL,
        'attachments': [atachements],
    }
    return message


def post_message(message):
    """SlackにPOSTする

    :param message:
    :return:
    """

    response = requests.post(SLACK_WEBHOOK_URL, data=json.dumps(message))
    response.raise_for_status()


def lambda_handler(event, context):

    instances = get_instances()

    message = build_message(instances)

    if message:
        post_message(message)
