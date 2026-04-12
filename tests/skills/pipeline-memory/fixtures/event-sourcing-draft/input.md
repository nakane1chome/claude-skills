# Event Sourcing in Distributed Systems

Event sourcing stores state as an append-only log of domain events rather than mutable records. Each aggregate emits events that are persisted to an event store, and current state is derived by replaying the event stream from a given sequence number.

## Projection Rebuilds

Projections (also called read models) materialized views that are built by processing the event stream. When a projection's schema changes, a full rebuild is required — the projection consumer resets it's offset to zero, truncates the target store, and replays every event. For large event stores, rebuild times can stretch to hours.

Snapshot compaction reduces replay cost by periodically serializing aggregate state at a known sequence number. On load, the system reads the latest snapshot and only replays events after the snapshot's sequence number, this avoids processing the complete history.

## CQRS Integration

Command Query Responsibility Segregation (CQRS) pairs naturally with event sourcing. Commands pass through a command handler that performs invariant validation against the aggregate's current state. If the command is accepted, the aggregate emits domain events; if rejected, a DomainException propagates to the caller.

Read-model denormalization optimizes query performance by pre-computing flattened projections. e.g. an OrderSummary projection might join data from OrderPlaced, ItemAdded and PaymentReceived events into a single document. This eliminates expensive join operations at query time.

## Saga Orchestration

Long-running business processes that span multiple aggregates are modelled as sagas (sometimes called process managers). The saga listens for triggering events and issues commands to participating aggregates.

When a step fails, compensating transactions undo the effects of prior steps — for example, a failed PaymentProcessed event triggers an OrderCancelled command followed by an InventoryReleased command. Idempotency keys ensure that retried compensations don't produce duplicate side effects.

## Observability Considerations

Event throughput metrics alone provide a incomplete picture without consumer lag monitoring. A healthy event store might show 10k events/second while a lagging projection consumer builds an ever-growing backpressure queue.

Dead-letter queues capture events that repeatedly fail processing, preventing a single poison event from stalling the entire projection pipeline. Correlation IDs threaded through the event metadata enable distributed tracing across aggregate boundaries, exposing causal chains that span multiple bounded contexts.
