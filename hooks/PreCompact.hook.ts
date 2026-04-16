#!/usr/bin/env bun
/**
 * PreCompact Hook — Preserve Algorithm state before context compaction
 *
 * WHEN: Fires before Claude Code compresses conversation context
 * WHY: Long Algorithm runs accumulate critical state (ISC criteria, decisions,
 *      verification evidence) that can be lost during auto-compaction.
 *
 * BEHAVIOR:
 * - On "auto" compaction: Backs up the most recent PRD to a snapshot file,
 *   then ALLOWS compaction (the Algorithm has context recovery via PRD).
 * - On "manual" compaction (/compact): Always allows — user explicitly chose this.
 *
 * The PRD serves as the system of record, so compaction is safe as long as
 * the PRD is up to date. This hook ensures a snapshot exists for recovery.
 */

import { readFileSync, writeFileSync, readdirSync, statSync, mkdirSync, existsSync } from 'fs';
import { join } from 'path';

const PAI_DIR = process.env.PAI_DIR || `${process.env.HOME}/.claude`;
const WORK_DIR = join(PAI_DIR, 'MEMORY', 'WORK');
const SNAPSHOT_DIR = join(PAI_DIR, 'MEMORY', 'SNAPSHOTS');

interface HookInput {
  hook_event_name: string;
  matcher_value: string; // "auto" or "manual"
}

async function main() {
  let input: HookInput;
  try {
    const stdin = readFileSync('/dev/stdin', 'utf-8');
    input = JSON.parse(stdin);
  } catch {
    // If we can't read input, allow compaction
    process.exit(0);
  }

  // Manual compaction (/compact) — always allow
  if (input.matcher_value === 'manual') {
    process.exit(0);
  }

  // Auto compaction — snapshot the most recent PRD before allowing
  try {
    if (!existsSync(WORK_DIR)) {
      process.exit(0);
    }

    // Find the most recently modified PRD
    const workDirs = readdirSync(WORK_DIR)
      .map(d => ({ name: d, path: join(WORK_DIR, d, 'PRD.md') }))
      .filter(d => {
        try { return statSync(d.path).isFile(); } catch { return false; }
      })
      .sort((a, b) => {
        const aStat = statSync(a.path);
        const bStat = statSync(b.path);
        return bStat.mtimeMs - aStat.mtimeMs;
      });

    if (workDirs.length === 0) {
      process.exit(0);
    }

    const latestPrd = workDirs[0];
    const prdContent = readFileSync(latestPrd.path, 'utf-8');

    // Check if this PRD is in an active phase (not complete)
    const phaseMatch = prdContent.match(/^phase:\s*(.+)$/m);
    const phase = phaseMatch?.[1]?.trim() || 'unknown';

    if (phase === 'complete') {
      // Completed work — compaction is safe, no snapshot needed
      process.exit(0);
    }

    // Active work — snapshot the PRD before compaction
    mkdirSync(SNAPSHOT_DIR, { recursive: true });
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const snapshotPath = join(SNAPSHOT_DIR, `${latestPrd.name}_${timestamp}.md`);
    writeFileSync(snapshotPath, prdContent);

    // Allow compaction — the Algorithm's context recovery reads from PRD
    process.exit(0);

  } catch {
    // On any error, allow compaction rather than blocking the session
    process.exit(0);
  }
}

main();
