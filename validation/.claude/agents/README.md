# Specialized Agents for Validation Framework

This directory contains agent specifications for Claude Code to use when working on the validation framework.

## Purpose

These agents help manage context efficiently by:
- Isolating complex tasks in separate contexts
- Returning concise summaries instead of full file contents
- Specializing in specific domains (coding vs analysis)
- Allowing longer main conversation sessions

## Available Agents

### python-coder.md
**Domain:** Python code modifications in validation framework

**Use for:**
- Adding new data collection functions
- Modifying test logic and completion criteria
- Updating timeout calculations
- Fixing bugs in test scripts
- Adding analysis tools

**Returns:** Summary of changes with file paths and line numbers

### test-analyzer.md
**Domain:** Test result analysis and issue identification

**Use for:**
- Analyzing test failures
- Comparing test sessions
- Identifying patterns in test data
- Investigating performance issues
- Root cause analysis

**Returns:** Insights and findings with supporting statistics

## How to Use

See [../AGENT_GUIDE.md](../AGENT_GUIDE.md) for detailed usage instructions and examples.

## Agent Design Principles

1. **Focused scope** - Each agent has a specific domain
2. **Concise output** - Return insights, not data dumps
3. **Self-contained** - Can work autonomously with minimal context
4. **Actionable results** - Provide clear next steps
5. **Context efficient** - Keep main conversation lean

## When to Create New Agents

Consider creating a new agent when:
- A task type is repeated frequently
- Working with large files that pollute context
- Specialized knowledge domain emerges
- Task requires deep iteration in isolation

## Agent Template

```markdown
# [Agent Name] Agent

You are a specialized agent for [specific purpose].

## Your Role
[What this agent does]

## Scope
[Files and tasks this agent handles]

## Guidelines
[How to approach the work]

## Communication Protocol
[Format for returning results]

## Important Context
[Key facts agent needs to know]
```
