# Asterisk on Docker Swarm

Reference deployment of `andrius/asterisk` as a Swarm service.

## Files

| File             | Purpose                                                   |
| ---------------- | --------------------------------------------------------- |
| `stack.yml`      | Compose v3.8 stack. Two variants: `asterisk-vip`, `asterisk-host`. |
| `.env.template`  | Copy to `.env`. Holds image tag and PUID/PGID.            |

## Quick start

```bash
cp .env.template .env
docker stack deploy -c stack.yml asterisk

docker stack services asterisk
docker service ps asterisk_asterisk-vip --no-trunc
docker service logs -f asterisk_asterisk-vip
```

Tear-down:

```bash
docker stack rm asterisk
# named volumes survive stack removal; remove explicitly if desired:
docker volume rm asterisk_asterisk-etc asterisk_asterisk-lib \
                 asterisk_asterisk-log asterisk_asterisk-spool
```

## Two variants, pick one

### `asterisk-vip` - overlay/VIP networking (default)

Published ports go through Swarm's IPVS load balancer. Trivially deployable
and multi-node ready, but IPVS rewrites the source IP - fine for internal SIP,
not ideal for carrier-facing trunks.

### `asterisk-host` - host networking (commented out)

Container shares the node's network namespace; source IPs preserved
end-to-end. Recommended for real SIP/RTP traffic.

Setup:

```bash
docker node update --label-add asterisk=true <node-name>
```

Then uncomment the `asterisk-host:` block in `stack.yml`. The image's RTP
range (10000-10199) and SIP ports (5060 udp/tcp, 5061 tcp) bind directly
on the host - no `ports:` block needed.

## PUID / PGID

Named volumes (the default) just work - the entrypoint chowns them at first
boot. For bind mounts, set `PUID` / `PGID` in `.env` to whatever owns the
host directory. Effective on Asterisk 10.x+ images only; pre-10.x ignores
the env vars and you must pre-chown to UID 1000 on the host.

## Updates

`update_config.order: stop-first` is set because two Asterisk replicas on
the same SIP port would conflict. Rolling updates therefore drop drained
calls during the gap. For zero-downtime upgrades, run an external SIP load
balancer (Kamailio / OpenSIPS) in front with two backends on different
SIP ports.

## Production checklist

- [ ] Mount your `pjsip.conf`, `extensions.conf`, `rtp.conf`, `modules.conf`
      via bind mounts or `docker config`.
- [ ] Set `EXTERNAL_IP`, `RTP_RANGE_START`, `RTP_RANGE_END` in those configs.
- [ ] Use the host-mode variant for real SIP traffic.
- [ ] Open the RTP port range on every node's external firewall.
- [ ] Pin to an exact image tag (`22.10.1_debian-trixie`), not `:latest`.
- [ ] Persist `/var/log/asterisk` to a named volume or external log shipper.
- [ ] If using bind mounts, set `PUID` / `PGID` to match host ownership.
