# Complete Oracle free-resource incorporation

Owner: Roosevelt Sanders. Platform: Sanders Dash & Seal. Spending budget: $0.

This is implemented application/catalog/inventory code. It does not create cloud resources, enable paid services, replace SQLite, or assert that a cloud deployment occurred. Published allowance figures are for observation and planning, not newly imposed deployment prerequisites.

## Three supplied sources

- [Oracle Quietly Halves Free Tier Ampere A1 Compute Limits with No Public Announcement](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/) — 2026-07-03. Capacity-change context; Oracle documentation controls entitlement.
- [Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) — 2026-06-12. Documented free-resource allowances and account/region conditions.
- [Viewing All Resources in a Compartment](https://docs.oracle.com/en-us/iaas/Content/General/Concepts/compartmentexplorer.htm) — 2026-09-18. Cross-region discovery, compartment hierarchy, eventual consistency and permission-filtered visibility; not a free-service price list.

## Full resource mapping

| Resource | Platform use | Recorded allowances |
|---|---|---|
| Certificates | Certificate inventory and service identity | certificate_authorities: 5; certificates: 150 |
| Ampere A1 Compute | Existing Node, Python, Nginx and SQLite runtime | ocpu_hours_per_month: 1500; memory_gb_hours_per_month: 9000; continuous_ocpus_total: 2; continuous_memory_gb_total: 12 |
| AMD Micro Compute | Optional lightweight supporting workloads | instances: 2; ocpus_per_instance: 0.125; memory_gb_per_instance: 1; internet_bandwidth_mbps_per_instance: 50; private_regional_bandwidth_mbps_up_to: 480 |
| Boot and block volumes | Persistent SQLite ledger, application data and volume backups | combined_storage_gb: 200; combined_volume_backups: 5 |
| Object and archive storage | Private ledger backups and release artifacts | free_only_combined_storage_gb: 20; api_requests_per_month: 50000; paid_or_trial_standard_gb: 10; paid_or_trial_infrequent_access_gb: 10; paid_or_trial_archive_gb: 10 |
| Vault keys and secrets | Store secrets and cryptographic key material without putting it in source | secrets: 150; hsm_key_versions_total: 20; versions_per_secret: 40; active_secret_versions_up_to: 20; pending_deletion_secret_versions_up_to: 20; software_key_versions: All included |
| Resource Manager | Repeatable deployment configuration and reviewable plans | configuration_source_providers: 100; concurrent_jobs: 2; job_duration_hours: 24; private_endpoints: 1; private_endpoint_reachable_ips: 100; private_templates: 100; stacks: 100; variables_per_stack: 250; bytes_per_variable: 8192; zip_mb_per_stack: 11 |
| Autonomous AI Database | Optional managed transaction, JSON, APEX or analytical database | instances: 2; ocpus_per_instance: 1; storage_gb_per_instance: 20; simultaneous_sessions_per_instance: 20 |
| Oracle NoSQL | Optional structured application and event state | tables: 3; storage_gb_per_table: 25; reads_per_month_up_to: 133000000; writes_per_month_up_to: 133000000 |
| MySQL HeatWave | Optional managed relational data service | standalone_db_systems: 1; heatwave_cluster_nodes: 1; database_storage_gb: 50; backup_storage_gb: 50 |
| Cluster placement groups | Optional compute placement organization | groups_minimum_documented: 10; groups_maximum_documented: 50 |
| Flexible Load Balancer | Optional HTTP routing across application backends | load_balancers: 1; minimum_bandwidth_mbps: 10; maximum_bandwidth_mbps: 10; listeners: 16; virtual_hostnames: 16; backend_sets: 16; backend_servers: 1024 |
| Network Load Balancer | Optional transport routing for the application | load_balancers: 1; listeners: 50; backend_sets: 50; backend_servers_per_set: 512; backend_servers_total: 1024 |
| Virtual cloud networks | Existing VCN, subnet and application network boundaries | free_only_vcns: 2 |
| VCN flow logs | Observe accepted and rejected network flows | shared_logging_gb_per_month: 10 |
| Site-to-Site VPN | Optional private connectivity to external networks | ipsec_connections_up_to: 50 |
| Application Performance Monitoring | Application diagnostics and availability observations | tracing_events_per_hour: 1000; synthetic_monitor_runs_per_hour: 10 |
| Connector Hub | Optional supported routing of application logs and events | connectors: 2 |
| Console dashboards | Platform operational overview | dashboards: 100 |
| Email Delivery | Customer notices and operational messages | emails_per_month: 3000 |
| Fleet Application Management | Optional lifecycle management of platform resources | managed_resources_per_month: 25 |
| Monitoring | Metrics and operational checks | ingestion_data_points: 500000000; retrieval_data_points: 1000000000 |
| Notifications | Operational alert delivery | https_notifications_per_month: 1000000; email_notifications_per_month: 1000 |
| Outbound data transfer | Deliver website, API and WebSocket responses | tb_per_month: 10 |
| Logging | Application, integrity and network operational logs | shared_gb_per_month_free_only: 10 |
| Bastion | Optional time-limited administrative connectivity | service_charge: Free |

## Account conditions and shared allocations

**Ampere A1 Compute**: VM.Standard.A1.Flex only; home region. An Instance observation alone does not identify its shape, OCPUs, memory or monthly consumption. Idle instances can be reclaimed under Oracle policy.

**AMD Micro Compute**: VM.Standard.E2.1.Micro only; eligible home-region availability domain. Boot storage shares the same 200-GB volume pool.

**Boot and block volumes**: Home region; boot and block volumes share the allocation. The supplied documentation describes 47-GB minimum and 50-GB default boot sizes in different sections; verify the actual image/volume selection.

**Object and archive storage**: Free-only: 20 GB combined across tiers. Paid/trial tier figures are separate account-state conditions, not extra free-only capacity. Trial paragraph separately describes the first 20 GB without credit deduction; do not infer a universal 30-GB trial allowance. Transition from trial requires respecting the documented storage allowance.

**Vault keys and secrets**: Virtual private vaults are excluded. The allocation is shared across vaults. Pending secret deletion does not immediately free capacity.

**Resource Manager**: A   f r e e   o r c h e s t r a t i o n   s e r v i c e   d o e s   n o t   m a k e   a l l   r e s o u r c e s   i n   i t s   T e r r a f o r m   p l a n   f r e e .

**Autonomous AI Database**: Regional availability and supported database versions vary. CPU and storage do not scale within the Always Free shape. No automatic replacement of the existing SQLite ledger.

**Oracle NoSQL**: Use an Always Free eligible table and supported region. The read/write figures preserve the owner-supplied catalog; verify actual service metering before sizing.

**MySQL HeatWave**: Home region and Always Free DB system selection. No automatic database migration or paid upgrade.

**Cluster placement groups**: E x a c t   e n t i t l e m e n t   d e p e n d s   o n   r e g i o n   a n d   s e r v i c e   p r i c i n g   m o d e l ;   t h e   r a n g e   i s   n o t   a   g u a r a n t e e d   a l l o c a t i o n   o f   5 0 .

**Flexible Load Balancer**: Applies to tenancies created December 15, 2020 or later. Both minimum and maximum must remain 10 Mbps for this free offering. Legacy Micro offering: 10 listeners/hostnames/backend sets and 128 servers, at 10 Mbps.

**Network Load Balancer**: B a c k e n d - s e r v e r   t o t a l   i s   s h a r e d   a c r o s s   b a c k e n d   s e t s .

**Virtual cloud networks**: Two-VCN figure applies to free-only tenancies without trial credits. Normal VCN objects are not additional VCN allocations. Outbound internet TCP 25 is blocked by default.

**VCN flow logs**: Shares the Logging allowance; it is not an additional 10 GB. Free-only tenancy condition in supplied documentation.

**Connector Hub**: Includes free and trial accounts. Connected source/target services have separate entitlements.

**Email Delivery**: Sender and domain configuration are separate setup work. No messages are sent by catalog incorporation.

**Fleet Application Management**: F i r s t   2 5   r e s o u r c e s   e a c h   m o n t h .

**Monitoring**: R e p o r t i n g   i n t e r v a l   f o r   t h e s e   n u m e r i c   a l l o c a t i o n s   i s   n o t   s t a t e d   i n   t h e   s u p p l i e d   e x c e r p t ;   v e r i f y   m e t e r i n g   p e r i o d .

**Notifications**: T h e s e   a r e   s e p a r a t e   f r o m   E m a i l   D e l i v e r y   m e s s a g e   a l l o w a n c e s .

**Outbound data transfer**: T r a n s f e r   v o l u m e   i s   n o t   a   t r a f f i c - r a t e   o r   c o n c u r r e n t - u s e r   g u a r a n t e e .

**Logging**: The supplied Logging section is truncated; the 10-GB shared figure is sourced from its VCN Flow Logs section. Do not add this to the flow-log amount.

**Bastion**: P r e s e n t   i n   t h e   c o m p l e t e   c u r r e n t   O r a c l e   A l w a y s   F r e e   p a g e   b e y o n d   t h e   s u p p l i e d   e x c e r p t ;   n o t   a n   S S H   p r e r e q u i s i t e .

## Application and scheduled inventory

- `/resources` presents all 26 categories and the roles of the three sources.
- `GET /api/platform/free-resources` returns only public documentation-derived catalog data. It needs no business adapter and exposes no tenant identifiers, credentials, usage snapshots or customer records. POST is refused.
- `python3 -m core_platform.free_resources` emits the machine-readable profile without contacting OCI.
- Existing six-hour OCI inventory reports include `free_resource_mapping`, even when observation is incomplete. Counts of related Search types are not shape, storage, monthly metering or billing evidence.
- Explicit arithmetic comparisons preserve unknown usage and do not provision, approve spending, or authorize privileged application operations.
- Instance Search records can correspond to A1, Micro or paid shapes. A generic instance observation never proves Always Free eligibility.
- All deployment/resource-creation defaults remain off. No OCI Apply or account upgrade occurred.

## Incorporation status

Every listed category is recorded, mapped to a platform role, packaged with the application and included in the read-only view/inventory coverage. This does not install provider-specific integrations or provision all listed products. Existing application and deployment integrations retain their actual status.

The supplied Logging section is cut off; the public Oracle page completes it with Logging and Bastion. Their provenance/conditions are explicit in the catalog. Pricing allowances for Functions and the paid Streaming service are not promoted to unlimited Always Free entitlements by the Tenancy Explorer supported-type list.
