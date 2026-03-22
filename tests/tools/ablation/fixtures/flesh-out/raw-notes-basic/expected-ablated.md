# Distributed Cache Management

Keeping caches consistent across services requires sending updates when data changes. When a record is deleted or modified, every cache holding that entry must be notified — otherwise other parts of the system serve old data.

Time-based expiration provides a safety mechanism but creates windows where old data is served during network issues. A network problem can delay update messages while the timer continues, leaving some systems serving expired entries.

A distribution method helps spread the load evenly across cache systems, but it makes it harder to adjust when systems are added or removed.

Storing writes in the cache before saving to the database introduces a data loss risk: if the cache system fails before saving completes, the buffered writes are lost.

## Removal Strategies

Standard removal of least-recently-used items performs poorly under certain access patterns — a single sequential read can remove the entire working set. Better algorithms handle these patterns more effectively.

Adding randomness to expiration times prevents the problem where many items expire at the same time and cause a burst of cache misses hitting the database.

A multi-level approach — a local cache backed by a shared cache — reduces overhead by keeping frequently accessed items in the application's memory and only going to the network cache when needed.

## Monitoring

Cache hit percentage alone is not useful without response time context. A high hit rate is meaningless if the small percentage of misses cause long delays that affect overall performance.

Tracking the cause of cache misses allows teams to tell apart new-system misses (empty cache after a restart) from update-related misses (cache was cleared by a competing change).

Connecting request traces across cache levels shows hidden complexity — a single request might trigger many cache lookups across multiple levels, and traces show where delays happen.
