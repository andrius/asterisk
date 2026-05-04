# Asterisk on Docker Swarm

A reference deployment of `andrius/asterisk` as a Swarm service, with the
gotchas, debugging recipes, and validation steps the project has accumulated
from real reports (most notably issue
[#86](https://github.com/andrius/asterisk/issues/86)).

## Files

| File                | Purpose                                                                 |
| ------------------- | ----------------------------------------------------------------------- |
| `stack.yml`         | The compose-v3.8 stack file. Two variants: `asterisk-vip`, `asterisk-host`. |
| `.env.template`     | Copy to `.env`. Holds image tag and PUID/PGID. `.env` is gitignored.    |

## Prerequisites

- A Swarm-mode Docker host (`docker swarm init` for a single-node test, or a
  proper multi-node cluster for production).
- For real SIP traffic: a public IP on the node (or proper NAT mapping), plus
  the RTP port range open in any upstream firewall.
- Asterisk **10.x or newer** if you want `PUID` / `PGID` env vars to work.
  Older images ignore them - they have no entrypoint hook.

## Quick start

```bash
cp .env.template .env
docker stack deploy -c stack.yml asterisk

# watch deployment
docker stack services asterisk
docker service ps asterisk_asterisk-vip --no-trunc

# stream logs
docker service logs -f asterisk_asterisk-vip
```

Tear-down:

```bash
docker stack rm asterisk
docker volume ls --filter label=com.docker.stack.namespace=asterisk
# named volumes are NOT removed automatically; remove manually if desired:
docker volume rm asterisk_asterisk-etc asterisk_asterisk-lib \
                 asterisk_asterisk-log asterisk_asterisk-spool
```

## Two variants, pick one

### A. `asterisk-vip` - overlay/VIP networking

Default Swarm behaviour: published ports go through Swarm's IPVS load balancer,
the service has a virtual IP, and traffic is round-robin'd to replicas.

**Pros:** trivially deployable, multi-node ready, replaces tasks transparently.

**Cons:** SIP via UDP behind IPVS works but you lose the original client IP
(IPVS rewrites the source). For pure dialplan testing or back-to-back
internal SIP this is fine. For carrier-facing trunks you usually want
host mode.

### B. `asterisk-host` (commented out by default)

Host networking: the container shares the node's network namespace and binds
the node's interfaces directly. No IPVS, no port translation, source IPs
preserved end-to-end.

Requirements:

- `mode: global` + a `node.labels.asterisk == true` placement constraint, so
  Swarm starts exactly one task on a known node.
- Label your target node first:

  ```bash
  docker node update --label-add asterisk=true <node-name>
  ```

- Skip the `ports:` block - host mode shares the host's network namespace.
- The image's RTP port range (10000-10199 by default) and SIP ports
  (5060 udp/tcp, 5061 tcp) bind directly on the host.

Uncomment the `asterisk-host:` block in `stack.yml` and (optionally) comment
out `asterisk-vip:` if you don't want both running.

## Common gotchas

### "It restarts itself every minute" (issue #86)

Symptom: container starts cleanly the first time, then ~1-2 minutes after
each (re)deploy Swarm replaces the task. Logs show nothing relevant.

Root cause was a SIGPIPE bug in the in-image healthcheck: under load,
`asterisk -rx "module show like res_pjsip" | grep -q res_pjsip` could return
non-zero spuriously, three failures in a row hit `retries=3`, and Swarm
replaced the task. Fixed in commit `a4ad877` (PR #110); rolled out to all
registry tags May 2026.

If you're seeing this on the current image, you're hitting something else -
inspect the actual healthcheck log:

```bash
task=$(docker service ps asterisk_asterisk-vip --format '{{.ID}}' --no-trunc | head -1)
node=$(docker service ps asterisk_asterisk-vip --format '{{.Node}}' --no-trunc | head -1)
# on the relevant node:
container=$(docker ps -q --filter "label=com.docker.swarm.task.id=${task}" | head -1)
docker inspect "$container" --format '{{json .State.Health}}' | jq
```

If `FailingStreak >= 1` and `Output` shows real errors (config syntax, missing
file, permission denied), fix that. If checks are all `exit=0` and the task
still restarts, the cause is elsewhere - check `docker service ps --no-trunc`
for the failure reason.

### Bind mounts and permissions

Named volumes (the default in `stack.yml`) "just work" - the entrypoint
chowns them at first boot. Bind mounts are different:

```yaml
volumes:
  - /srv/asterisk-etc:/etc/asterisk   # host dir, owned by some host UID
```

If the host dir's owner UID is not `1000` (the image default), set `PUID` /
`PGID` in `.env` to whatever owns the host dir. The Asterisk-10+ entrypoint
calls `usermod`/`groupmod`, then `chown -R` the runtime paths before starting.
If you're on a pre-10.x image, pre-chown the host dirs yourself
(`sudo chown -R 1000:1000 /srv/asterisk-etc`).

### `version: "3.8"` warning

Recent Docker versions print a deprecation warning about the `version:` key.
It's harmless; Swarm still parses it. Drop the line if it bothers you.

### Healthcheck and restart-policy interaction

The image ships with `--retries=3 --interval=30s --timeout=10s
--start-period=30s`. Combined with Swarm's restart-policy this means:

- After 30s grace, every 30s Swarm runs the check.
- After 3 consecutive failures (~90s), the task is marked `Failed`.
- The `restart_policy` block then schedules a replacement.

If your node is overloaded enough that `asterisk -rx ...` legitimately
takes longer than 10s, increase `timeout`:

```yaml
healthcheck:
  test: ["CMD", "/usr/local/bin/healthcheck.sh"]
  timeout: 20s
  retries: 5
```

### Updates without dropping calls

`stack.yml` sets `update_config.order: stop-first` because two replicas of the
same Asterisk on the same SIP port would conflict. That means there's a brief
gap during rolling updates - drained calls are dropped. For zero-downtime
upgrades you need an external SIP load balancer (Kamailio, OpenSIPS) with two
backends on different SIP ports.

## Validation: reproduce the issue-86 fix

If you want to verify the SIGPIPE fix landed in your tag:

```bash
# 1. pull and check the healthcheck source
docker pull andrius/asterisk:22
docker run --rm --entrypoint sh andrius/asterisk:22 \
  -c 'sed -n "92,96p" /usr/local/bin/healthcheck.sh'
# expected: `grep -q "$module" <<<"$module_output"`  (here-string, no pipe)
# old/buggy form:  `... | grep -q "$module" >/dev/null 2>&1`

# 2. deploy and watch
docker swarm init --advertise-addr 127.0.0.1   # if not already in swarm
cp .env.template .env
docker stack deploy -c stack.yml asterisk

# 3. observe healthcheck for a few minutes
container=$(docker ps -q --filter "label=com.docker.swarm.service.name=asterisk_asterisk-vip" | head -1)
for i in 1 2 3 4 5 6; do
  sleep 30
  docker inspect "$container" --format '{{.State.Health.Status}} fails={{.State.Health.FailingStreak}}'
done
# expected: 6x "healthy fails=0"

# 4. cleanup
docker stack rm asterisk
docker swarm leave --force
```

## Production checklist

Before pointing this at real traffic:

- [ ] Set `EXTERNAL_IP` / `RTP_RANGE_START`/`END` in `pjsip.conf` and `rtp.conf`.
- [ ] Mount your `pjsip.conf`, `extensions.conf`, `rtp.conf`, `modules.conf`
      (either via bind mounts or by `docker config create`-ing them and
      referencing as `configs:` in the stack).
- [ ] Use the host-mode variant unless you've explicitly tested IPVS+SIP.
- [ ] Open RTP port range on every node's external firewall.
- [ ] Pin to an exact image tag (`22.9.0_debian-trixie`) for reproducibility,
      not a moving alias like `:latest`.
- [ ] Capture `/var/log/asterisk` somewhere durable (named volume or external
      log shipper); the example uses an unnamed volume that's lost on stack
      removal.
- [ ] If using bind mounts, set `PUID`/`PGID` to match host ownership.
- [ ] Test failover: `docker service update --force asterisk_asterisk-vip` and
      confirm the new task starts cleanly and registers with your trunk.

## See also

- Project README: top-level [README.md](../../README.md) (especially the
  "Volume Permissions (PUID / PGID)" section for how the entrypoint works).
- Issue [#86](https://github.com/andrius/asterisk/issues/86) - the swarm
  restart-loop bug this example documents the fix for.
- Issue [#114](https://github.com/andrius/asterisk/issues/114) - bind-mount
  permission story behind the PUID/PGID feature.
- [Docker Compose v3.8 spec](https://docs.docker.com/reference/compose-file/legacy-versions/)
  for the (deprecated) `version: "3.8"` schema.
