==========================================
Feature parity of the TaaS service drivers
==========================================

Tap-as-a-Service ships two service drivers: the agent based driver for
ML2/OVS (``neutron_taas.services.taas.service_drivers.taas_rpc.TaasRpcDriver``
with the OVS and SR-IOV NIC agent drivers) and the OVN service driver for
ML2/OVN (``neutron_taas.services.taas.service_drivers.ovn.taas_ovn.TaasOvnDriver``).
They do not implement the same resources. The table below lists what each
driver supports; "no" means that the API call fails or has no effect with
that driver.

==========================================  ===================  ===================
Feature                                     ML2/OVS driver       ML2/OVN driver
==========================================  ===================  ===================
Tap services and tap flows                  yes                  no
Tap flow direction ``BOTH``                 yes                  n/a
VLAN filter on tap flows                    yes                  n/a
SR-IOV ports as tap flow source             yes (SR-IOV agent)   no
Tap mirrors ``gre`` / ``erspanv1``          yes                  yes
Tap mirror direction ``BOTH``               yes                  yes
Tap mirrors ``lport`` (Neutron port sink)   no                   yes, OVN 25.09+
Filtering rules on tap mirrors              no                   no
==========================================  ===================  ===================

Notes:

* With the OVN driver the tap service and tap flow calls fail with
  ``NotImplementedError``; use tap mirrors instead. An ``lport`` mirror
  covers the use case of tap services and tap flows, mirroring a port to
  another port of the cloud, without any tunnel.
* ``gre`` and ``erspanv1`` mirrors terminate the tunnel on the hypervisor
  with both drivers: the collector receives encapsulated traffic from the
  hypervisor address.
* With the OVN driver, traffic sent by the mirrored port is copied before its
  security groups are applied and traffic delivered to it after them; the
  copies bypass the security groups of the sink port. See
  :doc:`tap_mirrors_under_the_hood`.
* Filtering rules for ``lport`` mirrors (OVN ``Mirror_Rule``) are proposed
  in RFE https://bugs.launchpad.net/neutron/+bug/2168008.
