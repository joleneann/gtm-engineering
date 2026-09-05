#!/usr/bin/env bash
# Start the local n8n for this build.
#
# It died twice reading mail over IMAP: that trigger pulls every unread message
# in the mailbox, and a personal Gmail has years of them. Replies now come from
# the Gmail node over OAuth with a sender query, so nothing is fetched that is
# not a reply, and these limits stop the rest of n8n growing without bound.
#
# N8N_DIAGNOSTICS_ENABLED=false also silences the telemetry that retried a
# blocked host in a loop and held buffers while doing it.
export NODE_OPTIONS="--max-old-space-size=2048"
export N8N_DIAGNOSTICS_ENABLED=false
export N8N_VERSION_NOTIFICATIONS_ENABLED=false
export N8N_TEMPLATES_ENABLED=false
export EXECUTIONS_DATA_PRUNE=true
export EXECUTIONS_DATA_MAX_AGE=48
export EXECUTIONS_DATA_PRUNE_MAX_COUNT=50
export EXECUTIONS_DATA_SAVE_ON_SUCCESS=all
export EXECUTIONS_DATA_SAVE_ON_ERROR=all
export EXECUTIONS_DATA_SAVE_ON_PROGRESS=false
export EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS=true

# No Code node here runs Python, and n8n looks for a binary called python3 that
# Windows does not provide: it installs the py launcher instead. Saying so
# explicitly stops n8n trying to start a runner it cannot start.
export N8N_PYTHON_ENABLED=false

# Four settings whose defaults n8n is about to change. Each is pinned to the
# FUTURE default rather than the current one, so the next upgrade changes
# nothing here and the deprecation notice goes quiet. Nothing in this build
# installs community packages, runs a task longer than a second, or touches a
# compression node, so the tighter values cost nothing.
export N8N_UNVERIFIED_PACKAGES_ENABLED=false
export N8N_RUNNERS_TASK_TIMEOUT=60
export N8N_COMPRESSION_NODE_MAX_DECOMPRESSED_SIZE_BYTES=268435456
export N8N_COMPRESSION_NODE_MAX_ZIP_ENTRIES=1000

exec n8n start
