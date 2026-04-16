# PAI — Personal AI Infrastructure

A framework for building a persistent, skill-based AI assistant on top of [Claude Code](https://claude.ai/claude-code).

## What This Is

PAI turns Claude Code into a personalized AI system with:

- **The Algorithm** — A structured 7-phase execution framework (Observe → Think → Plan → Build → Execute → Verify → Learn) that produces verifiable outcomes using Ideal State Criteria
- **Skills** — Modular capability packages with workflows, tools, and routing
- **Hooks** — Lifecycle event handlers for security validation, context management, session learning, and system integrity
- **Memory** — Persistent file-based memory system for user context, project state, and learning reflections
- **TELOS** — A life operating system for tracking goals, projects, challenges, and personal growth

## Origin

This framework was originally designed and built by **Daniel**. This fork represents an evolution tailored to a specific user's mission — trading automation, Linux cloud infrastructure, and systematic market analysis.

We're sharing it back because the architecture is genuinely useful and because building on someone else's thoughtful work deserves acknowledgment.

## Structure

```
~/.claude/
├── PAI/                    # Core system (Algorithm, context routing, tools)
│   └── Algorithm/          # Versioned execution framework
├── skills/                 # Modular capabilities
│   ├── Trading/            # Market analysis, game plans, trade review
│   ├── Research/           # Multi-agent parallel research
│   ├── Thinking/           # FirstPrinciples, Council, RedTeam, Science
│   ├── Telos/              # Life OS — goals, projects, learning
│   ├── Agents/             # Custom agent composition
│   ├── USMetrics/          # Economic indicators
│   └── Utilities/          # System tools (upgrade, scaffolding, delegation)
├── hooks/                  # Lifecycle event handlers
├── MEMORY/                 # Persistent state (work, reflections, snapshots)
└── settings.json           # Configuration (permissions, hooks, MCP)
```

## Getting Started

1. Install [Claude Code](https://claude.ai/claude-code)
2. Copy this framework to `~/.claude/`
3. Create your `PAI/USER/` directory with your own TELOS, projects, and customizations
4. Create a `settings.json` from `settings.json.template`

## License

MIT — Use it, fork it, make it yours.

## Acknowledgments

- **Daniel** — Original PAI architect. Thank you for designing a system worth building on.
- **Anthropic** — For Claude Code and the model that makes this possible.
