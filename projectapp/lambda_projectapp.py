import time
import os
import boto3
import json
import urllib.request
import numpy as np
from datetime import datetime


logs = boto3.client("logs", region_name="us-east-2")


def cwlog(message):
    LOG_GROUP = os.environ["LOG_GROUP"]
    LOG_STREAM = "ApplicationLogs"
    global logs
    timestamp = int(round(time.time() * 1000))

    logs.put_log_events(
        logGroupName=LOG_GROUP,
        logStreamName=LOG_STREAM,
        logEvents=[
            {
                "timestamp": timestamp,
                "message": time.strftime("%Y-%m-%d %H:%M:%S") + "\t" + message,
            }
        ],
    )


def format_bullet_list(items, level=0):
    item_list = []
    if type(items) is list:
        for i in items:
            item_list.append(
                {"type": "rich_text_section", "elements": [{"type": "text", "text": i}]}
            )
    else:
        for k, v in items.items():
            item_list.append(
                {
                    "type": "rich_text_section",
                    "elements": [
                        {
                            "type": "link",
                            "text": v,
                            "url": "https://launchdarkly.atlassian.net/jira/core/projects/CPTT/board?selectedIssue="
                            + k,
                        }
                    ],
                }
            )
    retval = {
        "type": "rich_text",
        "elements": [
            {
                "type": "rich_text_list",
                "elements": item_list,
                "style": "bullet",
                "indent": level,
            }
        ],
    }

    return retval


def start_message():
    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Greetings!\n\nYour Product Specialists are hard at work serving SEs and customers alike. In addition, please review the following tasks from each of the Specialists:\n",
                },
            }
        ]
    }


def get_jira_data(jira_token):
    authtoken = "Basic " + jira_token
    headers = {"Accept": "application/json", "Authorization": authtoken}
    url = "https://launchdarkly.atlassian.net/rest/api/2/search?jql=project=CPTT&fields=assignee,progress,status,summary,resolutiondate&maxResults=1000"
    req = urllib.request.urlopen(
        urllib.request.Request(url, headers=headers, method="GET")
    )
    data = json.loads(req.read())
    return data["issues"]


def get_report_data(issues):
    statuses = ["To Do", "In Progress", "Done"]
    done_days = int(os.environ["DONE_DAYS"])
    spec_list = os.environ["SPECIALIST_LIST"]
    specialists = [x.strip() for x in spec_list.split(",")]

    owners = {}
    for item in issues:
        owner = item["fields"]["assignee"]["displayName"]
        if owner not in specialists:
            continue
        status = item["fields"]["status"]["name"]
        if status not in statuses:
            continue
        title = item["fields"]["summary"]
        done_date = item["fields"]["resolutiondate"]
        proceed = True
        if done_date is not None and status == "Done":
            dt1 = datetime.strptime(done_date, "%Y-%m-%dT%H:%M:%S.%f%z").replace(
                tzinfo=None
            )
            dt2 = datetime.now()
            if (dt2 - dt1).days > done_days:
                proceed = False
        if proceed == True:
            key = item["key"]
            if owner not in owners:
                owners[owner] = {}
            if status not in owners[owner]:
                owners[owner][status] = {}
            owners[owner][status][key] = title
    return owners


def populate_message(issue_data, out_data):
    t_keys = list(issue_data.keys())
    t_keys.sort()
    n_issue_data = {i: issue_data[i] for i in t_keys}
    for v in n_issue_data:
        out_data["blocks"].append(format_bullet_list([v], 0))
        t_keys = list(n_issue_data[v].keys())
        t_keys.sort(reverse=True)
        n_status = {i: n_issue_data[v][i] for i in t_keys}
        for l in n_status:
            out_data["blocks"].append(format_bullet_list([l], 1))
            nd_keys = list(n_status[l].keys())
            nd_values = list(n_status[l].values())
            v_index = np.argsort(nd_values)
            n_detail = {nd_keys[i]: nd_values[i] for i in v_index}
            out_data["blocks"].append(format_bullet_list(n_detail, 2))


def end_message(out_data):
    out_data["blocks"].append(
        {"type": "section", "text": {"type": "mrkdwn", "text": "\nThanks!\nCoE Team"}}
    )


def post_message(out_data, slack_webhook):
    json_payload = json.dumps(out_data)
    x = urllib.request.urlopen(
        urllib.request.Request(
            slack_webhook,
            data=json_payload.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
    )


def lambda_handler(event, context):
    slack_webhook = os.environ["SLACK_WEBHOOK"]
    jira_token = os.environ["JIRA_TOKEN"]

    cwlog("Entered handler successfully")
    payload = start_message()
    cwlog("Begin building message")
    populate_message(get_report_data(get_jira_data(jira_token)), payload)
    cwlog("Got message data")
    end_message(payload)
    cwlog("Complete building message")
    post_message(payload, slack_webhook)
    cwlog("Posted message to Slack")

    return {"isBase64Encoded": False, "statusCode": 200, "body": "Success!"}


####
# https://launchdarkly.atlassian.net/jira/core/projects/CPTT/board?selectedIssue=CPTT-22
####
