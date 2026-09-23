# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from neutron.tests import base
from neutron_lib.exceptions import taas as taas_exc

from neutron_taas.services.taas.service_drivers.ovn import match


class TestRuleToOvnMatch(base.BaseTestCase):

    def _rule(self, **kwargs):
        rule = {'ethertype': 'IPv4', 'protocol': None,
                'source_ip_prefix': None, 'destination_ip_prefix': None,
                'source_port_range_min': None, 'source_port_range_max': None,
                'destination_port_range_min': None,
                'destination_port_range_max': None}
        rule.update(kwargs)
        return rule

    def test_ethertype_only(self):
        self.assertEqual('ip4', match.rule_to_ovn_match(self._rule()))
        self.assertEqual('ip6', match.rule_to_ovn_match(
            self._rule(ethertype='IPv6')))

    def test_protocols(self):
        cases = {'tcp': 'ip4 && tcp', 'udp': 'ip4 && udp',
                 'sctp': 'ip4 && sctp', 'icmp': 'ip4 && icmp4'}
        for proto, expected in cases.items():
            self.assertEqual(expected, match.rule_to_ovn_match(
                self._rule(protocol=proto)))
        self.assertEqual('ip6 && icmp6', match.rule_to_ovn_match(
            self._rule(ethertype='IPv6', protocol='ipv6-icmp')))

    def test_prefixes(self):
        rule = self._rule(source_ip_prefix='192.168.20.0/24',
                          destination_ip_prefix='10.0.0.1/32')
        self.assertEqual(
            'ip4 && ip4.src == 192.168.20.0/24 && ip4.dst == 10.0.0.1/32',
            match.rule_to_ovn_match(rule))

    def test_single_port(self):
        rule = self._rule(protocol='tcp', destination_port_range_min=443,
                          destination_port_range_max=443)
        self.assertEqual('ip4 && tcp && tcp.dst == 443',
                         match.rule_to_ovn_match(rule))

    def test_port_range(self):
        rule = self._rule(protocol='udp', source_port_range_min=1000,
                          source_port_range_max=2000)
        self.assertEqual('ip4 && udp && udp.src >= 1000 && udp.src <= 2000',
                         match.rule_to_ovn_match(rule))

    def test_open_ended_port_range(self):
        rule = self._rule(protocol='tcp', destination_port_range_min=1024)
        self.assertEqual('ip4 && tcp && tcp.dst >= 1024 && tcp.dst <= 65535',
                         match.rule_to_ovn_match(rule))

    def test_full_rule(self):
        rule = self._rule(protocol='tcp',
                          source_ip_prefix='192.168.20.17/32',
                          destination_ip_prefix='10.0.0.0/24',
                          destination_port_range_min=80,
                          destination_port_range_max=443)
        self.assertEqual(
            'ip4 && tcp && ip4.src == 192.168.20.17/32 && '
            'ip4.dst == 10.0.0.0/24 && tcp.dst >= 80 && tcp.dst <= 443',
            match.rule_to_ovn_match(rule))

    def test_ports_without_l4_protocol(self):
        for proto in (None, 'icmp'):
            rule = self._rule(protocol=proto, destination_port_range_min=80)
            self.assertRaises(taas_exc.TapMirrorRuleInvalidPortRange,
                              match.rule_to_ovn_match, rule)

    def test_inverted_port_range(self):
        rule = self._rule(protocol='tcp', destination_port_range_min=90,
                          destination_port_range_max=80)
        self.assertRaises(taas_exc.TapMirrorRuleInvalidPortRange,
                          match.rule_to_ovn_match, rule)
