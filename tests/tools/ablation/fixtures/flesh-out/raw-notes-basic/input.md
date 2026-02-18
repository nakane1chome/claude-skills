# Distributed Cache Invalidation

- Cache coherence across microservices requires tombstone propagation
- TTL-based expiration creates stale read windows during partition events
- Consistent hashing mitigates hot-spot amplification but complicates rebalancing
- Write-behind caching introduces durability risk if the backing store lags

## Eviction Strategies

- LRU eviction degrades under scan-resistant workloads; consider ARC or LIRS
- Probabilistic early expiration (jittered TTL) prevents thundering herd on popular keys
- Hierarchical caching (L1 in-process, L2 distributed) reduces serialization overhead

## Observability

- Cache hit ratio alone is a vanity metric without latency percentile context
- Instrument miss-penalty attribution to distinguish cold starts from invalidation races
- Zipkin trace correlation across cache tiers exposes hidden fan-out amplification
