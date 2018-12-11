# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import time
import mock
from . import common
from datadog_checks.openstack_controller import OpenStackControllerCheck


def test_parse_uptime_string(aggregator):
    instance = common.MOCK_CONFIG["instances"][0]
    instance['tags'] = ['optional:tag1']
    init_config = common.MOCK_CONFIG['init_config']
    check = OpenStackControllerCheck('openstack_controller', init_config, {}, instances=[instance])
    uptime_parsed = check._parse_uptime_string(
        u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n')
    assert uptime_parsed.get('loads') == [0.04, 0.14, 0.19]


def test_cache_utils(aggregator):
    instance = common.MOCK_CONFIG["instances"][0]
    instance['tags'] = ['optional:tag1']
    init_config = common.MOCK_CONFIG['init_config']
    check = OpenStackControllerCheck('openstack_controller', init_config, {}, instances=[instance])
    check.CACHE_TTL['aggregates'] = 1
    expected_aggregates = {'hyp_1': ['aggregate:staging', 'availability_zone:test']}

    with mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_all_aggregate_hypervisors',
                    return_value=expected_aggregates):
        assert check._get_and_set_aggregate_list() == expected_aggregates
        time.sleep(1.5)
        assert check._is_expired('aggregates')


def get_server_details_response(params, timeout=None):
    if 'marker' not in params:
        return common.MOCK_NOVA_SERVERS_PAGINATED
    return common.EMPTY_NOVA_SERVERS


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_servers_detail',
            side_effect=get_server_details_response)
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_project_name_from_id',
            return_value="proj_name")
def test_get_paginated_server(servers_detail, project_name_from_id, aggregator):
    """
    Ensure the server cache is updated while using pagination
    """

    check = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS,
        'paginated_server_limit': 1
    }, {}, instances=common.MOCK_CONFIG)
    check.get_all_servers(True, "test_name")
    assert len(check.servers_cache) == 1
    assert 'server-1' in check.servers_cache['test_name']['servers']


OS_AGGREGATES_RESPONSE = [
    {
        "availability_zone": "london",
        "created_at": "2016-12-27T23:47:32.911515",
        "deleted": False,
        "deleted_at": None,
        "hosts": [
            "compute"
        ],
        "id": 1,
        "metadata": {
            "availability_zone": "london"
        },
        "name": "name",
        "updated_at": None,
        "uuid": "6ba28ba7-f29b-45cc-a30b-6e3a40c2fb14"
    }
]


def get_server_diagnostics_pre_2_48_response(server_id):
    return {
        "cpu0_time": 17300000000,
        "memory": 524288,
        "vda_errors": -1,
        "vda_read": 262144,
        "vda_read_req": 112,
        "vda_write": 5778432,
        "vda_write_req": 488,
        "vnet1_rx": 2070139,
        "vnet1_rx_drop": 0,
        "vnet1_rx_errors": 0,
        "vnet1_rx_packets": 26701,
        "vnet1_tx": 140208,
        "vnet1_tx_drop": 0,
        "vnet1_tx_errors": 0,
        "vnet1_tx_packets": 662,
        "vnet2_rx": 2070139,
        "vnet2_rx_drop": 0,
        "vnet2_rx_errors": 0,
        "vnet2_rx_packets": 26701,
        "vnet2_tx": 140208,
        "vnet2_tx_drop": 0,
        "vnet2_tx_errors": 0,
        "vnet2_tx_packets": 662
    }


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_server_diagnostics',
            side_effect=get_server_diagnostics_pre_2_48_response)
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_os_aggregates',
            return_value=OS_AGGREGATES_RESPONSE)
def test_get_stats_for_single_server_pre_2_48(server_diagnostics, os_aggregates, aggregator):
    check = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS,
        'paginated_server_limit': 1
    }, {}, instances=common.MOCK_CONFIG)

    check.get_stats_for_single_server({})

    aggregator.assert_metric('openstack.nova.server.vda_read_req', value=112.0,
                             tags=['availability_zone:NA'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.vda_read', value=262144.0,
                             tags=['availability_zone:NA'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.memory', value=524288.0,
                             tags=['availability_zone:NA'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.cpu0_time', value=17300000000.0,
                             tags=['availability_zone:NA'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                             tags=['availability_zone:NA'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.vda_write_req', value=488.0,
                             tags=['availability_zone:NA'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.vda_write', value=5778432.0,
                             tags=['availability_zone:NA'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                             tags=['availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx', value=140208.0,
                             tags=['availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                             tags=['availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx', value=2070139.0,
                             tags=['availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx_packets', value=662.0,
                             tags=['availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                             tags=['availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx_packets', value=26701.0,
                             tags=['availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                             tags=['availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                             tags=['availability_zone:NA', 'interface:vnet2'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx', value=140208.0,
                             tags=['availability_zone:NA', 'interface:vnet2'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                             tags=['availability_zone:NA', 'interface:vnet2'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx', value=2070139.0,
                             tags=['availability_zone:NA', 'interface:vnet2'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx_packets', value=662.0,
                             tags=['availability_zone:NA', 'interface:vnet2'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                             tags=['availability_zone:NA', 'interface:vnet2'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx_packets', value=26701.0,
                             tags=['availability_zone:NA', 'interface:vnet2'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                             tags=['availability_zone:NA', 'interface:vnet2'],
                             hostname='')

    aggregator.assert_all_metrics_covered()
