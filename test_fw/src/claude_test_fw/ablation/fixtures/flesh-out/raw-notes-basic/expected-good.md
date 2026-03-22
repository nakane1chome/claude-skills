# Distributed Cache Invalidation

Maintaining cache coherence across a microservices architecture demands reliable tombstone propagation. When a record is deleted or updated, every cache node holding that entry must receive the invalidation signal — otherwise downstream consumers serve stale data.

TTL-based expiration provides a safety net but creates stale read windows during network partition events. A partition can delay invalidation messages while the TTL clock continues ticking, leaving some nodes serving expired entries.

Consistent hashing mitigates hot-spot amplification by distributing keys evenly across cache nodes, but it complicates rebalancing when nodes join or leave the cluster.

Write-behind caching (buffering writes in the cache before flushing to the backing store) introduces a durability risk: if the cache node crashes before the flush completes, buffered writes are lost.

## Eviction Strategies

Standard LRU eviction degrades under scan-resistant workloads — a single sequential scan can evict the entire working set. Adaptive algorithms like ARC (Adaptive Replacement Cache) or LIRS (Low Inter-reference Recency Set) handle these workloads more gracefully.

Probabilistic early expiration (applying jittered TTL offsets) prevents the thundering herd problem where many keys expire simultaneously and trigger a burst of cache misses.

Hierarchical caching — an L1 in-process cache backed by an L2 distributed cache — reduces serialization overhead by keeping hot entries in the application's memory space and only falling through to the network cache on L1 misses.

## Observability

Cache hit ratio alone is a vanity metric without latency percentile context. A 99% hit ratio is meaningless if the 1% of misses incur 500ms penalties that dominate tail latency.

Instrumenting miss-penalty attribution allows teams to distinguish cold-start misses (empty cache after deployment) from invalidation races (cache was cleared by a competing update).

Zipkin trace correlation across cache tiers exposes hidden fan-out amplification — a single user request might trigger dozens of cache lookups across multiple tiers, and traces reveal where latency accumulates.
