# InfluxDB + Grafana integration for k6

Optional real-time monitoring during load runs.

## k6 output to InfluxDB

Run k6 with InfluxDB output:

```bash
k6 run scenarios/workflow-load.js --config config/normal-load.json \
  --out influxdb=http://localhost:8086/k6
```

With authentication (set env or use URL):

```bash
K6_INFLUXDB_ORGANIZATION=myorg K6_INFLUXDB_TOKEN=your-token \
k6 run ... --out influxdb=http://localhost:8086/k6
```

See [k6 InfluxDB output](https://grafana.com/docs/k6/latest/results-output/real-time/influxdb/) for URL options and env vars.

## Grafana dashboard

1. Add InfluxDB as a data source in Grafana (same URL/org/token).
2. Use the [k6 Grafana dashboard](https://grafana.com/grafana/dashboards/2587) (ID 2587) or build a custom dashboard from `k6_*` metrics (e.g. `http_reqs`, `http_req_duration`, `vus`, custom metrics like `ai_response_time`).

## Docker (optional)

For a local InfluxDB + Grafana stack:

- InfluxDB: `docker run -d -p 8086:8086 influxdb:2`
- Grafana: `docker run -d -p 3000:3000 grafana/grafana`

Configure the InfluxDB data source in Grafana to point at your InfluxDB URL.
