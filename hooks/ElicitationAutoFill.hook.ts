#!/usr/bin/env bun
/**
 * ElicitationAutoFill.hook.ts — Auto-fill MCP elicitation prompts
 *
 * WHEN: Fires on ElicitationResult — after user responds to an MCP elicitation
 * WHY: MCP servers (Gmail, Notion, Slack, Calendar, etc.) sometimes request
 *      re-authentication or consent prompts that interrupt workflow.
 *      This hook can auto-accept known-safe elicitations and log all others
 *      for review.
 *
 * BEHAVIOR:
 * - Known-safe MCP auth prompts: auto-accept
 * - Unknown prompts: pass through (let user decide)
 * - All elicitations logged to MEMORY/LOGS/elicitations.jsonl for audit
 *
 * TRIGGER: Elicitation (PreToolUse-style — fires when MCP server requests input)
 */

import { readFileSync, appendFileSync, mkdirSync, existsSync } from 'fs';
import { join } from 'path';

const PAI_DIR = process.env.PAI_DIR || `${process.env.HOME}/.claude`;
const LOG_DIR = join(PAI_DIR, 'MEMORY', 'LOGS');
const LOG_FILE = join(LOG_DIR, 'elicitations.jsonl');

interface ElicitationInput {
  hook_event_name: string;
  tool_name?: string;
  tool_input?: {
    server_name?: string;
    message?: string;
    [key: string]: unknown;
  };
  mcp_server_name?: string;
}

// MCP servers we trust for auto-consent on auth re-prompts
const TRUSTED_MCP_SERVERS = [
  'claude.ai Gmail',
  'claude.ai Google Calendar',
  'claude.ai Google Drive',
  'claude.ai Notion',
  'claude.ai Slack',
  'claude.ai Hugging Face',
];

function logElicitation(input: ElicitationInput, action: string) {
  try {
    if (!existsSync(LOG_DIR)) {
      mkdirSync(LOG_DIR, { recursive: true });
    }
    const entry = {
      timestamp: new Date().toISOString(),
      server: input.mcp_server_name || input.tool_input?.server_name || 'unknown',
      message: input.tool_input?.message || '',
      action,
    };
    appendFileSync(LOG_FILE, JSON.stringify(entry) + '\n');
  } catch {
    // Logging failure should never block the hook
  }
}

async function main() {
  let input: ElicitationInput;
  try {
    const stdin = readFileSync('/dev/stdin', 'utf-8');
    input = JSON.parse(stdin);
  } catch {
    process.exit(0); // Can't parse — pass through
  }

  const serverName = input.mcp_server_name || input.tool_input?.server_name || '';
  const isTrusted = TRUSTED_MCP_SERVERS.some(s => serverName.includes(s));

  if (isTrusted) {
    logElicitation(input, 'auto-accepted');
    // Allow the elicitation — trusted MCP server
    process.exit(0);
  }

  // Unknown server — log and pass through for user decision
  logElicitation(input, 'passed-through');
  process.exit(0);
}

main();
