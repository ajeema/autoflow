# AutoFlow Continuous Learning Demo

This demo shows how AutoFlow can **continuously improve a system over multiple runs**.

## Key Difference

| Regular Demo | Continuous Demo |
|--------------|-----------------|
| One-shot optimization | Iterative improvement |
| Temporary storage | Persistent database |
| Starts fresh each run | Remembers all previous runs |
| Good for experimentation | Good for production systems |

## How It Works

Each time you run the script:

```
┌─────────────────────────────────────────────────────────────┐
│  Run 1: Initial State                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Load Config │─▶│ Test System │─▶│AutoFlow    │        │
│  │ (v1, basic)│  │ (5 Qs)      │  │Analyzes    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                              │             │
│                                              ▼             │
│                                      ┌─────────────┐      │
│                                      │Propose      │      │
│                                      │Improve      │      │
│                                      │Structure    │      │
│                                      └─────────────┘      │
│                                              │             │
│                                              ▼             │
│                                      ┌─────────────┐      │
│                                      │Apply & Save │      │
│                                      │(v2, better) │      │
│                                      └─────────────┘      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Run 2: Builds on Run 1                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Load Config │─▶│ Test System │─▶│AutoFlow    │        │
│  │ (v2, better)│  │ (5 Qs)      │  │Analyzes ALL│        │
│  └─────────────┘  │             │  │history     │        │
│                   └─────────────┘  └─────────────┘        │
│                           │                                │
│         Sees Run 1 + Run 2 data combined!                 │
│                           │                                │
│                           ▼                                │
│                   Proposes next improvement                │
│                   (e.g., "Add code examples")             │
│                           │                                │
│                           ▼                                │
│                   Apply & Save (v3)                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Run 3+: Converges on Optimal                              │
│                                                             │
│  Each run sees ALL historical data and proposes            │
│  incremental improvements until quality target met.        │
│                                                             │
│  Eventually: "No improvements needed - threshold met"      │
└─────────────────────────────────────────────────────────────┘
```

## Running the Demo

```bash
# Install dependencies
pip install openai "autoflow[ai]"

# Set your OpenAI API key
export OPENAI_API_KEY=your_key_here

# Run multiple times - each run improves the system!
python3 continuous_demo.py  # Run 1: Basic → Structured
python3 continuous_demo.py  # Run 2: Structured → +Code Examples
python3 continuous_demo.py  # Run 3: +Code Examples → +Confidence
python3 continuous_demo.py  # Run 4: ...
```

## What You'll See

### Run 1 (Starting from scratch)
```
Current Configuration:
  Version: 1
  System prompt: You are a helpful assistant. Answer the question.

Phase 1: Testing Current System
  [1/5] What is Python?... ✓ quality: 45%
  [2/5] What is a variable?... ✓ quality: 52%
  ...

Current Performance:
  Success rate: 60%
  P95 latency: 850ms

Phase 2: AutoFlow Analysis
  Historical analysis (5 runs):
    Average quality: 54%
    Top issues: [('unstructured', 5), ('too_short', 3)]

  Generated 1 proposal(s):
    Title: Enforce structured response format
    Description: Historical answers lack structure. Adding structured format requirements.

Phase 3: Applying Improvements
  ✓ Applied: v1 → v2
```

### Run 2 (Building on Run 1)
```
Current Configuration:
  Version: 2
  System prompt: You are a precise technical assistant. Structure every answer...
  Last improved: 2025-01-15T10:30:00

Phase 1: Testing Current System
  [1/5] What is a list?... ✓ quality: 72%
  [2/5] What is a function?... ✓ quality: 68%
  ...

Current Performance:
  Success rate: 75%  ← Improved!
  P95 latency: 920ms

Phase 2: AutoFlow Analysis
  Historical analysis (10 runs):  ← Now sees Run 1 + Run 2 data!
    Average quality: 68%
    Top issues: [('missing_code_example', 6)]

  Generated 1 proposal(s):
    Title: Require code examples for technical questions
    Description: Historical technical answers lack code examples.

Phase 3: Applying Improvements
  ✓ Applied: v2 → v3
```

### Run 3+ (Converging)
```
Current Configuration:
  Version: 4
  System prompt: You are an expert technical assistant. Structure every answer
                with: ## Summary, ## Explanation, ## Examples. ALWAYS include
                runnable code examples...

Phase 1: Testing Current System
  Current Performance:
    Success rate: 88%  ← Continuing to improve!

Phase 2: AutoFlow Analysis

  ✓ System is performing well! No improvements needed.
  (Quality threshold already met)
```

## Persistent State

The demo creates a `.autoflow_workspace/` directory:

```
.autoflow_workspace/
├── continuous_learning.db      # SQLite database with all events
├── prompts.json                # Current prompt configuration
└── improvement_history.jsonl   # History of all improvements
```

### `prompts.json` - Current Configuration
```json
{
  "system_prompt": "You are a precise technical assistant...",
  "temperature": 0.5,
  "max_tokens": 500,
  "model": "gpt-4o-mini",
  "version": 3,
  "last_improved": "2025-01-15T10:35:00"
}
```

### `improvement_history.jsonl` - Improvement History
```json
{"timestamp": "2025-01-15T10:30:00", "old_version": 1, "new_version": 2, "proposal_title": "Enforce structured response format", ...}
{"timestamp": "2025-01-15T10:35:00", "old_version": 2, "new_version": 3, "proposal_title": "Require code examples for technical questions", ...}
```

## Key Features

### 1. **Historical Context**
- Each run analyzes ALL previous runs, not just the current one
- AutoFlow learns from cumulative experience
- Proposals get more targeted over time

### 2. **Incremental Improvement**
- Builds on previous improvements
- Each version is a small, safe change
- Avoids large, risky jumps

### 3. **Convergence**
- System improves until it hits quality threshold
- Eventually stops proposing changes
- Converges on optimal configuration

### 4. **Safety**
- Each proposal evaluated before application
- Shadow evaluation prevents bad changes
- Version tracking allows rollback

## Customization

### Adjust Learning Threshold
```python
ContinuousImprovementRule(
    workflow_id="qa_system",
    quality_threshold=0.80,  # Stop when 80% quality reached
)
```

### Change Test Questions Per Run
```python
questions = get_test_questions(count=10)  # Test more questions per run
```

### Adjust Improvement Speed
```python
# More aggressive improvements (fewer runs needed)
quality_threshold=0.70

# More conservative improvements (more runs, safer)
quality_threshold=0.90
```

### Reset Learning
```bash
# Delete workspace to start fresh
rm -rf .autoflow_workspace/
```

## Real-World Analogy

This is similar to how production systems improve:

| Demo | Production System |
|------|-------------------|
| Each run = iteration | Each day/week = iteration |
| Quality score = business metric | Conversion rate, customer satisfaction |
| Prompt config = system parameters | Model parameters, routing rules |
| `.autoflow_workspace/` = database | Production database |
| `improvement_history.jsonl` = changelog | Git history, audit logs |

## When to Use Each Demo

| Use Regular Demo When | Use Continuous Demo When |
|----------------------|--------------------------|
| Learning AutoFlow concepts | Building production systems |
| Testing rule logic | Implementing iterative optimization |
| Quick experimentation | Long-term improvement loops |
| One-shot optimization needed | Continuous monitoring needed |

## Cost

Each run makes **5-8 OpenAI API calls** using `gpt-4o-mini`.
Estimated cost: **$0.01 - $0.02 per run**.

Running 10 times to see convergence: **$0.10 - $0.20 total**.

## Next Steps

1. Run the demo 5-10 times to see the full learning curve
2. Check `.autoflow_workspace/improvement_history.jsonl` to see the progression
3. Try resetting and running with different quality thresholds
4. Modify the questions pool to test different domains
5. Add your own improvement rules!
