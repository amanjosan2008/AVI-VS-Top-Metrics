#!/usr/bin/env python
#
# Created on August 3, 2018
# @author: aman@avinetworks.com
#
# AVI-SDK based Script to get a list of VIPs using highest Bandwidth or no of Connections
#
# Requires AVI-SDK of same version as Controller: e.g: sudo pip install avisdk==17.2.11b1
# Real Time Metrics in AVI needs to be enabled for the VIPs
#
# Usage:-
#  python vs_metrics_top.py -c <controller-ip> -u <user-name> -p <password> -t <tenant> -a <api-version> -l <limits> -s <step> -pm <parameter>
#  python vs_metrics_top.py -c '10.140.196.5' -u 'admin' -p 'Admin@123' -t 'admin' -a '17.2.11' -l '10' -s '300' -pm 'bw'
#  python vs_metrics_top.py -c '10.140.196.5' -u 'admin' -p 'Admin@123' -t 'admin' -a '17.2.11' -l '10' -s '300' -pm 'conn'
#
# step denotes the duration granularity of the metrics aggregation.
# step=300 means the average, sum, max etc are computed using metrics in 5min duration window.
# The metrics API would return one value every 5min as denoted by step.
# Avi solution supports step=300,3600,86400 values.
#
# Here are some examples
# 1. Get metrics for last 6hrs: limit=72 & step=300
# 2. Get metrics for last 1day: limit=288 & step=300
# 3. Get latest single metric: limit=1 & step=300

from avi.sdk.avi_api import ApiSession
from avi.sdk.utils.api_utils import ApiUtils
from requests import urllib3
import json, sys
import argparse

def metrics(vs_uuid, m_id, tenant, step, limits):
    mq = {
            'metric_id': m_id,
            'tenant': 'admin',
            'step': step,
            'limit': limits,
            'entity_uuid': vs_uuid
        }
    api_utils = ApiUtils(api)
    rsp = api_utils.get_metrics_collection(metric_requests=[mq])
    total_value = 0
    for data in rsp['series'][vs_uuid][0]['data']:
        total_value += data['value']
    return total_value/limits

def top_vips(param, m_id):
    if (len(param) < 10):
        a = len(param)
    else:
        a = 10
    print '\nTop', a, 'VIPs:\n'
    print '{0: <45}'.format("VIP Name"), '{0: <12}'.format("Value"), '{0: <10}'.format("SE List")
    for i in range(a):
        key,value = max(param.items(), key = lambda p: p[1])
        resp2 = api.get('virtualservice/?name=%s' %key)
        try:
            se_list = []
            uuid = resp2.json()['results'][0]['vip_runtime'][0]['se_list']
            for i in uuid:
                se_uuid = i['se_ref'].split('/')[-1]
                resp3 = api.get('serviceengine/%s' %se_uuid)
                se_list.append(resp3.json()['name'].encode('ascii','ignore'))
        except KeyError:
            se_list.append("No SE attached to VIP")
        if m_id == 'l4_client.avg_complete_conns':
            print '{0: <45}'.format(key), '{0: <10}'.format(str((round(value,2)))+' Avg CPS'), str(se_list)[1:-1]
        else:
            print '{0: <45}'.format(key), '{0: <10}'.format(str((round(value/(1000*1000),2)))+' Mbps'), str(se_list)[1:-1]
        param.pop((max(param, key=param.get)))

def main():
    parser = argparse.ArgumentParser(description="AVISDK based Script to get a list of VIPs using highest Bandwidth or no of Connections")
    parser.add_argument("-u", "--username", required=False, help="Login username")
    parser.add_argument("-p", "--password", required=True, help="Login password")
    parser.add_argument("-c", "--controller", required=True, help="Controller IP address")
    parser.add_argument("-t", "--tenant", required=False, help="Tenant Name")
    parser.add_argument("-a", "--api_version", required=True, help="API Version")
    parser.add_argument("-l", "--limits", required=True, help="No of Samples to be taken")
    parser.add_argument("-s", "--step", required=True, help="Take samples after every n seconds - possible values 300,3600,86400")
    parser.add_argument("-pm", "--parameter", required=True, help="Parameter to be checked - possible values: bw, conn")

    args = parser.parse_args()

    user = str([args.username if args.username else "admin"][0])
    tenant = str([args.tenant if args.tenant else "admin"][0])
    api_version = str([args.api_version if args.api_version else "17.2.11"][0])
    password = args.password
    controller = args.controller
    limits = int(args.limits)
    step = int(args.step)
    if args.parameter == 'conn':
        m_id = 'l4_client.avg_complete_conns'
    elif args.parameter == 'bw':
        m_id = 'l4_client.avg_bandwidth'
    else:
        print 'Invalid Parameter, exitting.'
        sys.exit()

    # Get Api Session
    urllib3.disable_warnings()
    global api
    api = ApiSession.get_session(controller, user, password, tenant=tenant, api_version=api_version)

    vs_list = {}
    resp = api.get('virtualservice?page_size=3000')
    for vs in resp.json()['results']:
        vs_list.update({vs['name']:vs['uuid']})

    dic = {}
    for k,v in vs_list.items():
        name = k.encode('ascii','ignore')
        uuid = v.encode('ascii','ignore')
        avg_value = metrics(uuid, m_id, tenant, step, limits)
        dic.update({name:avg_value})

    print '\nTotal VIPs in Tenant:', tenant, ':', len(vs_list)
    print 'Average Values over past', (step * limits)/(60*60), 'hours (', (step * limits)/60, 'min) Collected Samples:', limits, 'each after:', step, 'sec'
    top_vips(dic, m_id)

if __name__ == "__main__":
main()
