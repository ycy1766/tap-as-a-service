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

"""Translate Tap Mirror rules into OVN ``Mirror_Rule`` match expressions.

A Tap Mirror rule is described with the same vocabulary as a security group
rule (ethertype, protocol, IP prefixes, port ranges). The OVN backend needs a
Logical_Flow match expression instead, for example::

    {'ethertype': 'IPv4', 'protocol': 'tcp',
     'destination_ip_prefix': '10.0.0.0/24',
     'destination_port_range_min': 443, 'destination_port_range_max': 443}
    -> 'ip4 && tcp && ip4.dst == 10.0.0.0/24 && tcp.dst == 443'

The translation is a pure function so it can be unit tested without OVN and
so that the API never exposes the OVN expression language to users.
"""

import netaddr
from neutron_lib import constants

from neutron_taas.extensions import tap_mirror_rules as rules_ext

_ETHERTYPE_TO_OVN = {
    constants.IPv4: 'ip4',
    constants.IPv6: 'ip6',
}

_PROTOCOL_TO_OVN = {
    constants.PROTO_NAME_TCP: 'tcp',
    constants.PROTO_NAME_UDP: 'udp',
    constants.PROTO_NAME_SCTP: 'sctp',
    constants.PROTO_NAME_ICMP: 'icmp4',
    constants.PROTO_NAME_IPV6_ICMP: 'icmp6',
}

# Protocols that carry L4 port numbers in OVN match expressions.
_L4_PROTOCOLS = (constants.PROTO_NAME_TCP, constants.PROTO_NAME_UDP,
                 constants.PROTO_NAME_SCTP)

# Match expression that selects every packet (OVN "true").
MATCH_ALL = '1'

# Protocols that imply an IP version.
_PROTOCOL_ETHERTYPE = {
    constants.PROTO_NAME_ICMP: constants.IPv4,
    constants.PROTO_NAME_IPV6_ICMP: constants.IPv6,
}


def _prefix_ethertype(prefix):
    if netaddr.IPNetwork(prefix).version == 6:
        return constants.IPv6
    return constants.IPv4


def _port_range_expr(field, range_min, range_max):
    if range_min is None and range_max is None:
        return None
    if range_min is None:
        range_min = 1
    if range_max is None:
        range_max = 65535
    if range_min > range_max:
        raise rules_ext.TapMirrorRuleInvalidPortRange(
            reason='%s range %s-%s: min is greater than max' %
            (field, range_min, range_max))
    if range_min == range_max:
        return '%s == %d' % (field, range_min)
    return '%s >= %d && %s <= %d' % (field, range_min, field, range_max)


def rule_to_ovn_match(rule):
    """Return the OVN match expression of a Tap Mirror rule dict.

    A rule without any match attribute matches every frame (``1``). The
    ethertype is taken from ``ethertype`` when given, otherwise it is
    derived from the IP prefixes or from an IP version specific protocol
    (``icmp`` is IPv4, ``ipv6-icmp`` is IPv6); a rule with none of them
    matches both IP versions.

    :param rule: dict with the ``rules`` sub-resource attributes.
    :raises TapMirrorRuleInvalidMatch: when the IP prefixes or the protocol
        disagree with each other or with ``ethertype``.
    :raises TapMirrorRuleInvalidPortRange: when a port range is invalid or
        used with a protocol that has no ports.
    """
    protocol = rule.get('protocol')
    ethertype = rule.get('ethertype')
    implied = []
    for key in ('source_ip_prefix', 'destination_ip_prefix'):
        prefix = rule.get(key)
        if prefix:
            implied.append((key, _prefix_ethertype(prefix)))
    if protocol in _PROTOCOL_ETHERTYPE:
        implied.append(('protocol', _PROTOCOL_ETHERTYPE[protocol]))
    for key, value in implied:
        if ethertype is None:
            ethertype = value
        elif value != ethertype:
            raise rules_ext.TapMirrorRuleInvalidMatch(
                reason='%s requires ethertype %s, got %s' %
                (key, value, ethertype))

    parts = []
    if ethertype:
        parts.append(_ETHERTYPE_TO_OVN[ethertype])
    if protocol:
        parts.append(_PROTOCOL_TO_OVN[protocol])

    ip = _ETHERTYPE_TO_OVN.get(ethertype)
    if rule.get('source_ip_prefix'):
        parts.append('%s.src == %s' % (ip, rule['source_ip_prefix']))
    if rule.get('destination_ip_prefix'):
        parts.append('%s.dst == %s' % (ip, rule['destination_ip_prefix']))

    port_fields = (
        ('src', rule.get('source_port_range_min'),
         rule.get('source_port_range_max')),
        ('dst', rule.get('destination_port_range_min'),
         rule.get('destination_port_range_max')),
    )
    has_ports = any(v is not None for _, lo, hi in port_fields
                    for v in (lo, hi))
    if has_ports and protocol not in _L4_PROTOCOLS:
        raise rules_ext.TapMirrorRuleInvalidPortRange(
            reason='port ranges require protocol %s' %
            '/'.join(_L4_PROTOCOLS))
    for direction, lo, hi in port_fields:
        if lo is None and hi is None:
            continue
        parts.append(_port_range_expr(
            '%s.%s' % (_PROTOCOL_TO_OVN[protocol], direction), lo, hi))

    return ' && '.join(parts) if parts else MATCH_ALL
