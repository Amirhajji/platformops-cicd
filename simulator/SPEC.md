# PlatformOPS simulator: reference spec (frozen v1.1)

All values are frozen in `simulator/config/` (run.yaml, kpis.yaml, components/*.yaml). The exact algorithm is in section 9 of PlatformOPS_Simulator_Specification.pdf.

## 1. Scope

8 components. Metric names, units, ranges and periods come from Huawei's official docs. The full list is in `huawei_metrics_catalog.csv`.

| C | Component | Namespace | Metrics | Resources |
|---|---|---|---|---|
| C1 | GaussDB(DWS) | SYS.DWS | 22 | 1 cluster, 3 nodes |
| C2 | DMS for Kafka | SYS.DMS | 41 | 1 instance, 3 brokers, 1 topic, 1 consumer group |
| C3 | ECS loader host | SYS.ECS + AGT.ECS | 77 | 1 server |
| C4 | ECS bastion | SYS.ECS | 17 | 1 server |
| C5 | OBS | SYS.OBS | 95 | 1 bucket |
| C6 | NAT gateway | SYS.NAT | 17 | 1 gateway |
| C7 | VPC network | SYS.VPC | 10 | 2 EIPs, 5 subnets |
| C8 | CCE | AOM | 62 | 1 cluster, 2 nodes, 3 workloads |

Total: 341 metrics, 504 columns.

## 2. Logic

**x, metrics (generated).** Each metric has a normal interval and a bad interval, both inside its official range.
- Normal period: a random value in the normal interval.
- Bad period: a random value in the bad interval.
- Values are rounded to the unit: % stays within 0–100, counts are whole numbers.
- Fixed-size metrics (total disk, CPU cores, total IPs) stay constant.

**y, KPIs.** 2–5 per component. Each KPI is one of:
- Average: y = (x₁ + … + xₙ) / n
- Maximum: y = max(x₁ … xₙ)
- Ratio: y = 100 × part / total

**h, health score (0–100).** Each KPI has a good value G and a bad value B:
- at G or better: h = 100
- at B or worse: h = 0
- in between: h = 100 × (B − y) / (B − G)

**z, KQIs.**
- Component score: z = average of its KPI health scores.
- Global score: Z = average of the 8 component scores.
- Status: 80–100 healthy · 50–79 degraded · 0–49 critical.

## 2b. KPI table (frozen)

| C | KPI ID | Name | Signal | Type | Formula | G | B | Better |
|---|---|---|---|---|---|---|---|---|
| C1 | dws_cpu | CPU load | saturation | average | avg of dws010_cpu_usage over nodes | 60 | 90 | lower |
| C1 | dws_mem | Memory load | saturation | average | avg of dws011_mem_usage over nodes | 70 | 90 | lower |
| C1 | dws_disk | Disk fill | saturation | maximum | max of dws015_disk_usage over nodes | 70 | 90 | lower |
| C1 | dws_cache | Cache efficiency | latency | value | dws001_shared_buffer_hit_ratio | 95 | 80 | higher |
| C1 | dws_io_wait | Disk write latency | latency | maximum | max of dws021_avg_disk_sec_per_write over nodes | 0.01 | 0.1 | lower |
| C2 | kafka_backlog | Consumer backlog | latency | value | consumer_messages_remained | 1000 | 100000 | lower |
| C2 | kafka_disk | Broker disk fill | saturation | maximum | max of broker_disk_usage over brokers | 70 | 90 | lower |
| C2 | kafka_cpu | Broker CPU | saturation | average | avg of broker_cpu_usage over brokers | 60 | 90 | lower |
| C2 | kafka_alive | Brokers alive | errors | ratio | 100 × (sum(broker_alive)) / (count(broker)) | 100 | 66 | higher |
| C2 | kafka_produce_lat | Produce latency | latency | maximum | max of broker_produce_mean over brokers | 10 | 100 | lower |
| C3 | ldr_cpu | CPU load | saturation | value | cpu_usage | 60 | 90 | lower |
| C3 | ldr_mem | Memory load | saturation | value | mem_usedPercent | 70 | 90 | lower |
| C3 | ldr_disk | Disk fill | saturation | value | disk_usedPercent | 70 | 90 | lower |
| C3 | ldr_iowait | I/O wait | latency | value | cpu_usage_iowait | 5 | 30 | lower |
| C3 | ldr_retrans | TCP retransmission | errors | value | net_tcp_retrans | 1 | 5 | lower |
| C4 | bst_cpu | CPU load | saturation | value | cpu_util | 60 | 90 | lower |
| C4 | bst_disk | Disk fill | saturation | value | disk_util_inband | 70 | 90 | lower |
| C4 | bst_conn | Open connections | traffic | value | network_vm_connections | 50 | 500 | lower |
| C5 | obs_err | Error rate | errors | ratio | 100 × (request_count_4xx + request_count_5xx) / (get_request_count + put_request_count + post_request_count + head_request_count + delete_request_count) | 1 | 5 | lower |
| C5 | obs_success | Request success | errors | value | request_success_rate | 99.9 | 95 | higher |
| C5 | obs_latency | Request latency | latency | value | total_request_latency | 100 | 1000 | lower |
| C5 | obs_first_byte | First byte delay | latency | value | first_byte_latency | 50 | 500 | lower |
| C6 | nat_snat | SNAT connection usage | saturation | value | snat_connection_ratio | 50 | 80 | lower |
| C6 | nat_out_bw | Outbound bandwidth usage | saturation | value | outbound_bandwidth_ratio | 60 | 90 | lower |
| C6 | nat_drops | Dropped packets | errors | maximum | max of packets_drop_count_snat_connection_beyond, packets_drop_count_pps_beyond, packets_drop_count_eip_port_alloc_beyond | 0 | 100 | lower |
| C7 | eip_out | EIP outbound usage | saturation | maximum | max of upstream_bandwidth_usage over EIP / bandwidths | 60 | 90 | lower |
| C7 | eip_in | EIP inbound usage | saturation | maximum | max of downstream_bandwidth_usage over EIP / bandwidths | 60 | 90 | lower |
| C7 | subnet_ip | Subnet IP usage | saturation | maximum | max of subnet_ipv4_availability_usage_percentage over subnets | 70 | 90 | lower |
| C8 | cce_cpu | Cluster CPU | saturation | value | aom_cluster_cpu_usage | 60 | 90 | lower |
| C8 | cce_mem | Cluster memory | saturation | value | aom_cluster_memory_usage | 70 | 90 | lower |
| C8 | cce_node_disk | Node disk fill | saturation | maximum | max of aom_node_disk_usage over nodes | 70 | 90 | lower |
| C8 | cce_pod_mem | Workload memory | saturation | maximum | max of aom_container_memory_usage over containers | 70 | 90 | lower |
| C8 | cce_workloads_ok | Workloads healthy | errors | ratio | 100 × (count(aom_process_status == 0)) / (count(container)) | 100 | 66 | higher |

Full spec with generation rules, output contract, compatibility and acceptance checks: PlatformOPS_Simulator_Specification.pdf.

## 3. Run

- 7 days, 1 row per minute, 10,080 rows.
- 3 bad periods per component, at fixed times.
- Seed 42: the same run always gives the same data.
- Output: one CSV per component, plus `labels.csv` listing the bad periods.

## 4. Not in the model

No propagation between components, no hidden states, no daily curve.
