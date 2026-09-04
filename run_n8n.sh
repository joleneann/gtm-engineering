#!/usr/bin/env bash
# Start the local n8n for this build.
#
# It died once at a 2 GB heap: the IMAP trigger pulls every unread message in
# the mailbox, and a personal Gmail has years of them. The node is filtered to
# today's mail, and these limits stop the rest of n8n growing without bound.
#
# N8N_DIAGNOSTICS_ENABLED=false also silences the telemetry that retried a
# blocked host in a loop and held buffers while doing it.
export NODE_OPTIONS="--max-old-space-size=1024"
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
exec n8n start
