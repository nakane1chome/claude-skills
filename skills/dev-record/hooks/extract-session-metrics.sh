#!/bin/bash
# Extract token usage, estimated cost, and compaction events from Claude Code's
# native session log (~/.claude/projects/...).
#
# Usage: extract-session-metrics.sh <SESSION_ID> <PROJECT_DIR>
# Outputs a JSON object to stdout. Outputs '{}' if the session log is not found.

set -euo pipefail

SESSION_ID="${1:-}"
PROJECT_DIR="${2:-}"

if [ -z "$SESSION_ID" ] || [ -z "$PROJECT_DIR" ]; then
  echo '{}'
  exit 0
fi

# Derive the Claude session log path.
# Claude Code stores logs at ~/.claude/projects/<path-with-slashes-as-dashes>/<session>.jsonl
PROJECT_HASH=$(echo "$PROJECT_DIR" | tr '/' '-')
SESSION_LOG="$HOME/.claude/projects/${PROJECT_HASH}/${SESSION_ID}.jsonl"

if [ ! -f "$SESSION_LOG" ]; then
  echo '{}'
  exit 0
fi

# ---------------------------------------------------------------------------
# Pricing table (per million tokens, public API pricing as of 2025)
# Format: prefix|input|output|cache_read|cache_creation
# ---------------------------------------------------------------------------
PRICING_TABLE='claude-opus-4|15|75|1.5|18.75
claude-sonnet-4|3|15|0.3|3.75
claude-haiku-4|1|5|0.1|1.25
claude-haiku-3-5|0.8|4|0.08|1'

# ---------------------------------------------------------------------------
# Extract all data in a single jq pass (avoids multiple reads of large files)
# ---------------------------------------------------------------------------
# Claude session logs may contain malformed lines (e.g. truncated writes).
# Use fromjson? to skip unparseable lines in a single pass before slurping.
jq -cR 'fromjson? // empty' "$SESSION_LOG" | jq -s --arg pricing "$PRICING_TABLE" '
  # Split events by type
  ([ .[] | select(.type == "assistant" and .message.usage) ] ) as $assistants |
  ([ .[] | select(.type == "system" and .subtype == "compact_boundary") ]) as $compactions |

  # Aggregate token usage
  {
    input_tokens:                 ([ $assistants[].message.usage.input_tokens                 // 0 ] | add // 0),
    output_tokens:                ([ $assistants[].message.usage.output_tokens                // 0 ] | add // 0),
    cache_read_input_tokens:      ([ $assistants[].message.usage.cache_read_input_tokens      // 0 ] | add // 0),
    cache_creation_input_tokens:  ([ $assistants[].message.usage.cache_creation_input_tokens  // 0 ] | add // 0)
  } as $usage |

  # Extract model from first assistant message
  ($assistants[0].message.model // null) as $model |

  # Compute estimated cost
  (if $model then
    # Parse pricing table: find first matching prefix
    ($pricing | split("\n") | map(split("|")) |
      map(select(.[0] as $pfx | $model | startswith($pfx))) |
      first // null
    ) as $rate |
    if $rate then
      (($usage.input_tokens                * ($rate[1] | tonumber) / 1e6) +
       ($usage.output_tokens               * ($rate[2] | tonumber) / 1e6) +
       ($usage.cache_read_input_tokens     * ($rate[3] | tonumber) / 1e6) +
       ($usage.cache_creation_input_tokens * ($rate[4] | tonumber) / 1e6))
      | . * 10000 | round / 10000
    else null end
  else null end) as $cost |

  # Extract compaction events
  [
    $compactions[] |
    {
      timestamp: .timestamp,
      trigger:   (.compactMetadata.trigger // "unknown"),
      pre_tokens: (.compactMetadata.preTokens // 0)
    }
  ] as $comp_events |

  # Output
  {
    token_usage: $usage,
    model: $model,
    estimated_cost_usd: $cost,
    compactions: {
      count: ($comp_events | length),
      events: $comp_events
    }
  }
'
