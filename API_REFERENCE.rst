==============================
Tap as a Service Tap Mirror rules
----------------

With the ``tap-mirror-rules`` extension, ``lport`` mirrors accept filtering
rules as the ``rules`` sub-resource (``/taas/tap_mirrors/{tap_mirror_id}/rules``). Rules are evaluated by
decreasing ``priority`` (1-32767); the first matching rule decides whether
the packet is mirrored (``action: mirror``) or not (``action: skip``). A
packet matching no rule is mirrored, so a mirror without rules mirrors the
whole traffic of the port; to mirror only selected traffic add a low priority
catch-all ``skip`` rule. A rule applies to every direction mirrored by its
Tap Mirror unless ``direction`` (``IN`` or ``OUT``) restricts it. The match
is described like a security group rule:

.. code-block:: python

    'rules': {
        'id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None}, 'is_visible': True,
               'primary_key': True},
        'project_id': {'allow_post': True, 'allow_put': False,
                       'validate': {'type:string': None},
                       'required_by_policy': True, 'is_visible': True},
        'priority': {'allow_post': True, 'allow_put': False,
                     'validate': {'type:range': (1, 32767)},
                     'is_visible': True},
        'action': {'allow_post': True, 'allow_put': False,
                   'validate': {'type:values': ['mirror', 'skip']},
                   'default': 'mirror', 'is_visible': True},
        'direction': {'allow_post': True, 'allow_put': False,
                      'validate': {'type:values': ['IN', 'OUT', None]},
                      'default': None, 'is_visible': True},
        'ethertype': {'allow_post': True, 'allow_put': False,
                      'validate': {'type:values': ['IPv4', 'IPv6']},
                      'default': 'IPv4', 'is_visible': True},
        'protocol': {'allow_post': True, 'allow_put': False,
                     'validate': {'type:values': ['tcp', 'udp', 'sctp',
                                                  'icmp', 'ipv6-icmp',
                                                  None]},
                     'default': None, 'is_visible': True},
        'source_ip_prefix': {'allow_post': True, 'allow_put': False,
                             'validate': {'type:subnet_or_none': None},
                             'default': None, 'is_visible': True},
        'destination_ip_prefix': {'allow_post': True, 'allow_put': False,
                                  'validate': {'type:subnet_or_none': None},
                                  'default': None, 'is_visible': True},
        'source_port_range_min': {'allow_post': True, 'allow_put': False,
                                  'validate': {'type:range_or_none':
                                               (1, 65535)},
                                  'default': None, 'is_visible': True},
        'source_port_range_max': {'allow_post': True, 'allow_put': False,
                                  'validate': {'type:range_or_none':
                                               (1, 65535)},
                                  'default': None, 'is_visible': True},
        'destination_port_range_min': {'allow_post': True,
                                       'allow_put': False,
                                       'validate': {'type:range_or_none':
                                                    (1, 65535)},
                                       'default': None, 'is_visible': True},
        'destination_port_range_max': {'allow_post': True,
                                       'allow_put': False,
                                       'validate': {'type:range_or_none':
                                                    (1, 65535)},
                                       'default': None, 'is_visible': True},
    }

Port ranges are only accepted with the ``tcp``, ``udp`` and ``sctp``
protocols. Two rules of the same mirror cannot share the same priority,
direction and match.


API REFERENCE
==============================

This documents is an API REFERENCE for Tap-as-a-Service Neutron extension.

The documents is organized into the following sections:
* TaaS Resources
* API Reference
* TaaS CLI Reference
* Workflow

TaaS Resources
==============

TaaS consists of two resources, TapService and TapFlow.

TapService
----------

TapService Represents the port on which the mirrored traffic is delivered.
Any service (VM) that uses the mirrored data is attached to the port.

.. code-block:: python

    'tap_services': {
        'id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None}, 'is_visible': True,
               'primary_key': True},
        'tenant_id': {'allow_post': True, 'allow_put': False,
                      'validate': {'type:string': None},
                      'required_by_policy': True, 'is_visible': True},
        'name': {'allow_post': True, 'allow_put': True,
                 'validate': {'type:string': None},
                 'is_visible': True, 'default': ''},
        'description': {'allow_post': True, 'allow_put': True,
                        'validate': {'type:string': None},
                        'is_visible': True, 'default': ''},
        'port_id': {'allow_post': True, 'allow_put': False,
                    'validate': {'type:uuid': None},
                    'is_visible': True},
    }

TapFlow
-------

TapFlow Represents the port from which the traffic needs to be mirrored.

.. code-block:: python

    'tap_flows': {
        'id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None}, 'is_visible': True,
               'primary_key': True},
        'tenant_id': {'allow_post': True, 'allow_put': False,
                      'validate': {'type:string': None},
                      'required_by_policy': True, 'is_visible': True},
        'name': {'allow_post': True, 'allow_put': True,
                 'validate': {'type:string': None},
                 'is_visible': True, 'default': ''},
        'description': {'allow_post': True, 'allow_put': True,
                        'validate': {'type:string': None},
                        'is_visible': True, 'default': ''},
        'tap_service_id': {'allow_post': True, 'allow_put': False,
                           'validate': {'type:uuid': None},
                           'required_by_policy': True, 'is_visible': True},
        'source_port': {'allow_post': True, 'allow_put': False,
                        'validate': {'type:uuid': None},
                        'required_by_policy': True, 'is_visible': True},
        'direction': {'allow_post': True, 'allow_put': False,
                      'validate': {'type:values': direction_enum},
                      'is_visible': True},
        'vlan_filter': {'allow_post': True, 'allow_put': False,
                        'validate': {'type:regex_or_none': RANGE_REGEX},
                        'is_visible': True, 'default': None}
    }

    direction_enum = ['IN', 'OUT', 'BOTH']


Multiple TapFlow instances can be associated with a single TapService
instance.

Tap Mirror
----------

A ``tapmirror`` mirrors the traffic of a Neutron port using ``gre`` or
``erspan v1`` tunnels to a remote IP address, or, with the ``lport`` mirror
type, to another Neutron port inside the overlay (``remote_port_id``).

.. code-block:: python

    'tap_mirrors': {
        'id': {
            'allow_post': False, 'allow_put': False,
            'validate': {'type:uuid': None}, 'is_visible': True,
            'primary_key': True},
        'project_id': {
            'allow_post': True, 'allow_put': False,
            'validate': {'type:string': db_const.PROJECT_ID_FIELD_SIZE},
            'required_by_policy': True, 'is_filter': True,
            'is_sort_key': True, 'is_visible': True},
        'name': {
            'allow_post': True, 'allow_put': True,
            'validate': {'type:string': None},
            'is_visible': True, 'default': ''},
        'description': {
            'allow_post': True, 'allow_put': True,
            'validate': {'type:string': None},
            'is_visible': True, 'default': ''},
        'port_id': {
            'allow_post': True, 'allow_put': False,
            'validate': {'type:uuid': None},
            'enforce_policy': True, 'is_visible': True},
        'directions': {
            'allow_post': True, 'allow_put': False,
            'validate': DIRECTION_SPEC,
            'is_visible': True},
        'remote_ip': {
            'allow_post': True, 'allow_put': False,
            'validate': {'type:ip_address': None},
            'is_visible': True},
        'mirror_type': {
            'allow_post': True, 'allow_put': False,
            'validate': {'type:values': mirror_types_list},
            'is_visible': True},
    }

    mirror_types_list = ['erspanv1', 'gre']
    DIRECTION_SPEC = {
        'type:dict': {
            'IN': {'type:integer': None, 'default': None, 'required': False},
            'OUT': {'type:integer': None, 'default': None, 'required': False}
        }
    }

The ``tap-mirror-lport`` extension adds the ``lport`` value to
``mirror_type``, makes ``remote_ip`` optional and adds ``remote_port_id``:

.. code-block:: python

    'tap_mirrors': {
        'mirror_type': {
            'allow_post': True, 'allow_put': False,
            'validate': {'type:values': ['erspanv1', 'gre', 'lport']},
            'is_visible': True},
        'remote_ip': {
            'allow_post': True, 'allow_put': False,
            'validate': {'type:ip_address_or_none': None},
            'default': None, 'is_visible': True},
        'remote_port_id': {
            'allow_post': True, 'allow_put': False,
            'validate': {'type:uuid_or_none': None},
            'default': None, 'enforce_policy': True, 'is_visible': True},
    }

For an ``lport`` mirror ``remote_port_id`` is mandatory and ``remote_ip`` must
be unset; the remote port must be bound to a host, must differ from
``port_id`` and must belong to the same project unless the caller is an
administrator. The tunnel ID values of ``directions`` are optional and
ignored for this type, only the keys (``IN``, ``OUT``, ``BOTH``) select the
mirrored directions. A port can have at most one ``lport`` mirror per
direction (the backend installs one unconditional mirroring flow per mirror
and direction, two would collide); several ports may mirror to the same
remote port. Deleting either the mirrored port or the remote port deletes the
mirror.

The mirrored traffic is taken from the logical switch pipeline of the source
port: frames sent by the port are copied before the security group rules are
applied, frames delivered to the port are copied after them, i.e. only the
traffic the port actually receives. The copies bypass the security groups of
the remote port.

API REFERENCE
=============

https://docs.openstack.org/api-ref/network/v2/index.html#tap-as-a-service

TaaS CLI Reference
==================

Openstack CLI
-------------

OpenStackClient provides
`the basic network commands <https://docs.openstack.org/python-openstackclient/latest/cli/command-list.html>`__
and tap-as-a-service has an extension for taas related commands.

* Create tap service: **openstack tap service create** --name <name of the tap service> --port <name or ID of the port on which the traffic is delivered>

* List tap services: **openstack tap service list**

* Show tap service: **openstack tap service show** <tap service id/tap service name>

* Delete tap service: **openstack tap service delete** <tap service id/tap service name>

* Update tap service: **openstack tap service update** <tap service id/tap service name> --name <new name of the tap service> --description <new description of the tap service>

* Create tap flow: **openstack tap flow create** --name <name of the tap flow> --port <name or ID of the Source port to which the Tap Flow is connected> --tap-service <name or ID of the tap service> --direction <Direction of the Tap flow. Possible options are: IN, OUT, BOTH> --vlan-filter <LAN Ids to be mirrored in the form of range string>

* List tap flows **openstack tap flow list**

* Show tap flow **openstack tap flow show** <tap flow id/tap flow name>

* Delete tap flow **openstack tap flow delete** <tap flow id/tap flow name>

* Update tap flow **openstack tap flow update** <tap flow id/tap flow name> --name <new name of the tap flow> --description <new description of the tap flow>

Openstack CLI for tap mirrors
-----------------------------

* Create tap mirror: **openstack tap mirror create** --name <name of the tap mirror> --description <description for the tap mirror> --port <the name or UUID of the port to associate with the tap mirror> --directions <direction dict keys are IN and OUT, the value is the tunnel ID, i.e.: IN=102, can be repeated> --remote-ip <the destination of the mirroring> --mirror-type <can be gre or erspanv1>

* Create an lport tap mirror: **openstack tap mirror create** --name <name of the tap mirror> --port <the name or UUID of the port to mirror> --directions BOTH --remote-port <the name or UUID of the port receiving the mirrored traffic> --mirror-type lport

* Create a tap mirror rule: **openstack tap mirror rule create** <Name or ID of the tap mirror> --priority <1-32767> --action <mirror or skip> [--direction <IN or OUT>] [--ethertype <IPv4 or IPv6>] [--protocol <tcp, udp, sctp, icmp or ipv6-icmp>] [--src-ip <CIDR>] [--dst-ip <CIDR>] [--src-port <min[:max]>] [--dst-port <min[:max]>]

* List and delete tap mirror rules: **openstack tap mirror rule list** <Name or ID of the tap mirror>, **openstack tap mirror rule delete** <Name or ID of the tap mirror> <ID of the rule>

* List tap mirrors: **openstack tap mirror list**

* Show tap mirrors: **openstack tap mirror show** <Name or ID of the tap mirror>

* Delete tap mirror: **openstack tap mirror delete** <Name or ID of the tap mirror>

* Update tap mirror: **openstack tap mirror update** <Name or ID of the tap mirror> --name <name of the tap mirror> --description <description for the tap mirror>

Workflow
=========

In this section we describe a simple sequence of steps to use TaaS.

Workflow Sequence for tap services and tap flows
------------------------------------------------

1. Create a Neutron port with 'port_security_enabled' set to 'false'.

2. Launch a VM (VM on which you want to monitor/receive the mirrored data).
   Associate the Neutron port created in step 1 while creating the VM.

3. Using Neutron Client command for TaaS **neutron tap-service-create** or
   via REST APIs create a Tap Service instance by associating the port
   created in step 1.

4. Using Neutron Client command for TaaS **neutron tap-flow-create** or
   via REST APIs create a Tap Flow instance by associating the Tap Service
   instance created in step 3 and the target Neutron port from which you want
   to mirror traffic (assuming the Neutron port from which the traffic
   needs to be monitored already exists.)
   Mirroring can be done for both incoming and/or outgoing traffic from the
   target Neutron port.

5. Observe the mirrored traffic on the monitoring VM by running tools such as
   tcpdump.
