# Running Clip2Easy on Oracle Cloud (Always Free)

Oracle's Always Free ARM machine is the most capable free server available: **4 CPUs, 24 GB
RAM, 200 GB of disk**, free forever rather than as a trial. That is 25× the memory and 440×
the disk of the small container this project started on, which is where the out-of-memory
kills and "no space left" failures came from.

Everything here is free: the server, the HTTPS certificate, and (with Cloudflare R2) 10 GB of
media storage with no charge for downloads.

## 1. Create the machine

1. Sign up at <https://cloud.oracle.com> and pick a home region close to you. A card is asked
   for identity only; Always Free resources are not billed. If the region is full, try a
   different one — capacity moves around.
2. **Compute → Instances → Create instance**
   - Image: **Ubuntu 24.04**
   - Shape: **Ampere (ARM) VM.Standard.A1.Flex** → **4 OCPUs, 24 GB memory**
   - Boot volume: **200 GB**
   - Save the SSH key it offers; you need it to log in.
3. **Networking → Virtual Cloud Network → Security List** → add ingress rules for TCP **80**
   and **443** from `0.0.0.0/0`, or the site will be unreachable even though it is running.

## 2. Point a domain at it

Give the API a name (for example `api.yourdomain.com`) with an **A record** to the instance's
public IP. Caddy then gets a free HTTPS certificate on its own. Without a domain you can still
run it over plain HTTP by IP, but browsers will block the site's requests to it.

## 3. Install and start

```bash
ssh ubuntu@<your-instance-ip>
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker ubuntu && exec su -l ubuntu      # log back in so docker works

# Oracle images block traffic by default; open the two web ports.
sudo iptables -I INPUT 6 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save

git clone https://github.com/amazingappppsss/clipmaker.git && cd clipmaker/deploy/oracle
cp .env.example .env && nano .env        # fill in every value
docker compose up -d --build             # first build takes a few minutes
curl -s https://api.yourdomain.com/health
```

`/health` reports the machine it found and what it is missing:

```json
{"status":"ok","limits":{"memory_limit_mb":24000,"cpus":4,"encoder_threads":1},
 "transcription_ready":true,"llm_ready":true}
```

With 4 CPUs the renderer automatically renders **3 clips at once** instead of one.

## 4. Point the website at it

In Vercel, set `NEXT_PUBLIC_API_URL` to `https://api.yourdomain.com` and redeploy. Set
`CORS_ORIGINS` in `.env` to the site's address so the browser is allowed to call the API.

## Moving the data across

Projects and clips live in Postgres and in storage. The quickest clean start is to let people
re-create projects; to carry the old ones over instead:

```bash
# on the old host
pg_dump "$DATABASE_URL" -Fc -f clipmaker.dump
# on the new server
docker compose cp clipmaker.dump db:/tmp/ && \
  docker compose exec db pg_restore -U clipmaker -d clipmaker --clean /tmp/clipmaker.dump
```

Media files only need copying if you stayed on local storage; with R2 they are already there.

## Day to day

```bash
docker compose logs -f api worker     # what is happening
docker compose pull && docker compose up -d --build    # deploy a new version
docker compose exec db pg_dump -U clipmaker clipmaker > backup.sql   # back up
```
