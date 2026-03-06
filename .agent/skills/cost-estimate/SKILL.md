---
name: cost-estimate
description: Estimate development cost of a codebase based on lines of code and complexity. Use when the user wants to know what the codebase would cost to build from scratch.
version: 1.0.0
---

# Cost Estimate Command

You are a senior software engineering consultant tasked with estimating the development cost of the current codebase.

## Step 1: Analyze the Codebase

Read the entire codebase to understand:
- Total lines of code by language/file type
- Architectural complexity (frameworks, integrations, APIs)
- Advanced features (real-time, AI/ML, complex pipelines)
- Testing coverage
- Documentation quality

Use the Glob and Read tools to systematically review:
- All source files (TypeScript, SQL, etc.)
- All test files
- Build scripts and configuration files
- Edge functions, migrations, shared utilities

**Language detection**: Use `find . -type f -name "*.ts" -o -name "*.tsx" -o -name "*.sql" -o -name "*.css" | head -20` to identify the primary languages, then count lines per language using `wc -l` or `cloc` if available.

## Step 2: Calculate Development Hours

Based on industry standards for a **senior full-stack developer** (5+ years experience):

**Hourly Productivity Estimates**:
- Simple CRUD/UI code: 30-50 lines/hour
- Complex business logic: 20-30 lines/hour
- Database migrations & SQL functions: 15-25 lines/hour
- Edge functions / serverless: 20-30 lines/hour
- AI/ML pipeline integration: 10-20 lines/hour
- Webhook/API integrations: 15-25 lines/hour
- Real-time / event-driven systems: 10-20 lines/hour
- Comprehensive tests: 25-40 lines/hour
- DevOps / CI/CD configuration: 15-25 lines/hour

**Additional Time Factors**:
- Architecture & design: +15-20% of coding time
- Debugging & troubleshooting: +25-30% of coding time
- Code review & refactoring: +10-15% of coding time
- Documentation: +10-15% of coding time
- Integration & testing: +20-25% of coding time
- Learning curve (new frameworks): +10-20% for specialized tech

**Calculate total hours** considering:
1. Base coding hours (lines of code / productivity rate)
2. Multipliers for complexity and overhead
3. Specialized knowledge required (Supabase, Deno, AI scoring, etc.)

## Step 3: Research Market Rates

Use WebSearch to find current 2025-2026 hourly rates for:
- Senior full-stack developers (5-10 years experience)
- Specialized developers matching the tech stack
- Contractors vs. employees
- Geographic variations (US markets: SF Bay Area, NYC, Austin, Remote)

Search queries to use:
- "senior full stack developer hourly rate 2025"
- "senior TypeScript developer contractor rate 2025"
- "senior software engineer hourly rate United States 2025"
- "Supabase developer freelance rate 2025"

## Step 4: Calculate Organizational Overhead

Real companies don't have developers coding 40 hours/week. Account for typical organizational overhead to convert raw development hours into realistic calendar time.

**Weekly Time Allocation for Typical Company**:

| Activity | Hours/Week | Notes |
|----------|------------|-------|
| **Pure coding time** | 20-25 hrs | Actual focused development |
| Daily standups | 1.25 hrs | 15 min x 5 days |
| Weekly team sync | 1-2 hrs | All-hands, team meetings |
| 1:1s with manager | 0.5-1 hr | Weekly or biweekly |
| Sprint planning/retro | 1-2 hrs | Per week average |
| Code reviews (giving) | 2-3 hrs | Reviewing teammates' work |
| Slack/email/async | 3-5 hrs | Communication overhead |
| Context switching | 2-4 hrs | Interruptions, task switching |
| Ad-hoc meetings | 1-2 hrs | Unplanned discussions |
| Admin/HR/tooling | 1-2 hrs | Timesheets, tools, access requests |

**Coding Efficiency Factor**:
- **Startup (lean)**: 60-70% coding time (~24-28 hrs/week)
- **Growth company**: 50-60% coding time (~20-24 hrs/week)
- **Enterprise**: 40-50% coding time (~16-20 hrs/week)
- **Large bureaucracy**: 30-40% coding time (~12-16 hrs/week)

**Calendar Weeks Calculation**:
```
Calendar Weeks = Raw Dev Hours / (40 x Efficiency Factor)
```

## Step 5: Calculate Full Team Cost

Engineering doesn't ship products alone. Calculate the fully-loaded team cost including all supporting roles.

**Supporting Role Ratios** (expressed as ratio to engineering hours):

| Role | Ratio to Eng Hours | Typical Rate | Notes |
|------|-------------------|--------------|-------|
| Product Management | 0.25-0.40x | $125-200/hr | PRDs, roadmap, stakeholder mgmt |
| UX/UI Design | 0.20-0.35x | $100-175/hr | Wireframes, mockups, design systems |
| Engineering Management | 0.12-0.20x | $150-225/hr | 1:1s, hiring, performance, strategy |
| QA/Testing | 0.15-0.25x | $75-125/hr | Test plans, manual testing, automation |
| Project/Program Management | 0.08-0.15x | $100-150/hr | Schedules, dependencies, status |
| Technical Writing | 0.05-0.10x | $75-125/hr | User docs, API docs, internal docs |
| DevOps/Platform | 0.10-0.20x | $125-200/hr | CI/CD, infra, deployments |

**Full Team Multiplier**:
- **Solo/Founder**: 1.0x (just engineering)
- **Lean Startup**: ~1.45x engineering cost
- **Growth Company**: ~2.2x engineering cost
- **Enterprise**: ~2.65x engineering cost

## Step 6: Generate Cost Estimate

Provide a comprehensive estimate in this format:

---

## [Project Name] - Development Cost Estimate

**Analysis Date**: [Current Date]

### Codebase Metrics

- **Total Lines of Code**: [number]
  - [Language 1]: [number] lines
  - [Language 2]: [number] lines
  - Tests: [number] lines

- **Complexity Factors**:
  - Advanced frameworks: [list key ones]
  - Integrations: [list external services]
  - Specialized logic: [scoring pipelines, real-time, etc.]

### Development Time Estimate

**Base Development Hours**: [number] hours

**Overhead Multipliers**:
- Architecture & Design: +[X]% ([hours] hours)
- Debugging & Troubleshooting: +[X]% ([hours] hours)
- Code Review & Refactoring: +[X]% ([hours] hours)
- Documentation: +[X]% ([hours] hours)
- Integration & Testing: +[X]% ([hours] hours)
- Learning Curve: +[X]% ([hours] hours)

**Total Estimated Hours**: [number] hours

### Realistic Calendar Time (with Organizational Overhead)

| Company Type | Efficiency | Coding Hrs/Week | Calendar Weeks | Calendar Time |
|--------------|------------|-----------------|----------------|---------------|
| Solo/Startup (lean) | 65% | 26 hrs | [X] weeks | ~[X] months |
| Growth Company | 55% | 22 hrs | [X] weeks | ~[X] years |
| Enterprise | 45% | 18 hrs | [X] weeks | ~[X] years |
| Large Bureaucracy | 35% | 14 hrs | [X] weeks | ~[X] years |

### Market Rate Research

**Senior Full-Stack Developer Rates (current year)**:
- Low end: $[X]/hour (remote, mid-level market)
- Average: $[X]/hour (standard US market)
- High end: $[X]/hour (SF Bay Area, NYC, specialized)

**Recommended Rate for This Project**: $[X]/hour

### Total Cost Estimate

| Scenario | Hourly Rate | Total Hours | **Total Cost** |
|----------|-------------|-------------|----------------|
| Low-end | $[X] | [hours] | **$[X,XXX]** |
| Average | $[X] | [hours] | **$[X,XXX]** |
| High-end | $[X] | [hours] | **$[X,XXX]** |

**Recommended Estimate (Engineering Only)**: **$[X,XXX] - $[X,XXX]**

### Full Team Cost (All Roles)

| Company Stage | Team Multiplier | Engineering Cost | **Full Team Cost** |
|---------------|-----------------|------------------|-------------------|
| Solo/Founder | 1.0x | $[X] | **$[X]** |
| Lean Startup | 1.45x | $[X] | **$[X]** |
| Growth Company | 2.2x | $[X] | **$[X]** |
| Enterprise | 2.65x | $[X] | **$[X]** |

**Role Breakdown (Growth Company Example)**:

| Role | Hours | Rate | Cost |
|------|-------|------|------|
| Engineering | [X] hrs | $[X]/hr | $[X] |
| Product Management | [X] hrs | $[X]/hr | $[X] |
| UX/UI Design | [X] hrs | $[X]/hr | $[X] |
| Engineering Management | [X] hrs | $[X]/hr | $[X] |
| QA/Testing | [X] hrs | $[X]/hr | $[X] |
| Project Management | [X] hrs | $[X]/hr | $[X] |
| Technical Writing | [X] hrs | $[X]/hr | $[X] |
| DevOps/Platform | [X] hrs | $[X]/hr | $[X] |
| **TOTAL** | **[X] hrs** | | **$[X]** |

### Grand Total Summary

| Metric | Solo | Lean Startup | Growth Co | Enterprise |
|--------|------|--------------|-----------|------------|
| Calendar Time | [X] | [X] | [X] | [X] |
| Total Human Hours | [X] | [X] | [X] | [X] |
| **Total Cost** | **$[X]** | **$[X]** | **$[X]** | **$[X]** |

### Assumptions

1. Rates based on US market averages (current year)
2. Full-time equivalent allocation for all roles
3. Includes complete implementation of all current features
4. Does not include:
   - Marketing & sales
   - Legal & compliance
   - Office/equipment
   - Hosting/infrastructure
   - Ongoing maintenance post-launch

---

## Step 7: Calculate Claude ROI - Value Per Claude Hour

This answers: **"What did each hour of Claude's actual working time produce?"**

### 7a: Determine Actual Claude Clock Time

**Method 1: Git History (preferred)**

Run `git log --format="%ai" | sort` to get all commit timestamps. Then:
1. **First commit** = project start
2. **Last commit** = current state
3. Cluster commits into sessions (group commits within 4-hour windows)
4. Estimate session duration from commit density:
   - 1-2 commits in a window: ~1 hour session
   - 3-5 commits: ~2 hour session
   - 6-10 commits: ~3 hour session
   - 10+ commits: ~4 hour session

**Method 2: Fallback Estimate**

If no reliable timestamps, estimate from lines of code:
- Assume Claude writes 200-500 lines of meaningful code per hour
- Claude active hours = Total LOC / 350

### 7b: Calculate Value per Claude Hour

```
Value per Claude Hour = Total Code Value (from Step 5) / Estimated Claude Active Hours
```

### 7c: Claude Efficiency vs. Human Developer

**Speed Multiplier**:
```
Speed Multiplier = Human Dev Hours / Claude Active Hours
```

**Cost Efficiency**:
```
Human Cost = Human Hours x Average Rate
Claude Cost = Subscription + API costs
Savings = Human Cost - Claude Cost
ROI = Savings / Claude Cost
```

### 7d: Add ROI Section to Report

---

### Claude ROI Analysis

**Project Timeline**:
- First commit / project start: [date]
- Latest commit: [date]
- Total calendar time: [X] days ([X] weeks)

**Claude Active Hours Estimate**:
- Total sessions identified: [X] sessions
- Estimated active hours: [X] hours

**Value per Claude Hour**:

| Value Basis | Total Value | Claude Hours | $/Claude Hour |
|-------------|-------------|--------------|---------------|
| Engineering only | $[X] | [X] hrs | **$[X,XXX]/Claude hr** |
| Full team (Growth Co) | $[X] | [X] hrs | **$[X,XXX]/Claude hr** |

**Speed vs. Human Developer**:
- Estimated human hours for same work: [X] hours
- Claude active hours: [X] hours
- **Speed multiplier: [X]x**

**Cost Comparison**:
- Human developer cost: $[X]
- Estimated Claude cost: $[X] (subscription + API)
- **Net savings: $[X]**
- **ROI: [X]x**

---

## Notes

Present the estimate in a clear, professional format suitable for sharing with stakeholders. Include confidence intervals and key assumptions. Highlight areas of highest complexity that drive cost.
