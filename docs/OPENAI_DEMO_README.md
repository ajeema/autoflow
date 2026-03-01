# AutoFlow + OpenAI Demo

This demo demonstrates a **real AI workflow** where AutoFlow learns from OpenAI API outcomes and proposes improvements to prompts and parameters.

## What It Does

1. **Runs a QA System** using OpenAI's GPT-4o-mini
2. **Tracks Outcomes** for each API call:
   - Success/failure
   - Answer quality (via heuristics)
   - Latency
   - Cost
   - Token usage
3. **AutoFlow Analyzes** the data and detects:
   - Low quality answers
   - Common issues (too short, unstructured, missing examples, etc.)
4. **Proposes Improvements** to the system prompt
5. **Validates via Replay** on historical data with safety gates
6. **Applies Changes** only when gates pass
7. **Validates** improvements on new data

## Prerequisites

```bash
# Install dependencies
pip install openai "autoflow[ai]"

# Set your OpenAI API key
export OPENAI_API_KEY=your_key_here
```

## Running the Demo

```bash
python3 openai_demo.py
```

## Demo Workflow

### Phase 1: Initial Data Collection
- Tests 3 different prompt variants
- Runs 5 test questions through each variant
- Tracks quality metrics for each answer

### Phase 2: Baseline Metrics
- Computes aggregate metrics:
  - Success rate
  - Quality-adjusted success
  - P95 latency
  - Average cost

### Phase 3: AutoFlow Analysis
- Ingests all events into the context graph
- Runs the `LowQualityRule` to detect issues
- Generates proposals for prompt improvements

### Phase 4: Replay Evaluation
- Simulates each proposal on historical data
- Compares baseline vs candidate metrics
- Enforces safety gates:
  - Max 200ms latency regression
  - Max $0.005 cost increase
  - Min 5% success rate improvement

### Phase 5: Apply Improvements
- Applies proposals that pass safety gates
- Rejects proposals that would regress metrics

### Phase 6: Validation
- Tests the improved prompt on new questions
- Compares new metrics vs baseline
- Confirms improvement

## Example Output

```
--- Phase 3: AutoFlow Analysis ---

Ingested 15 events

Generated 1 proposal(s):

  Proposal: Add structured response format
    Description: Answers lack structure. Proposing prompt change to enforce structured output.
    Risk: RiskLevel.LOW
    Target: config/prompts.yaml

--- Phase 4: Replay Evaluation ---

  Proposal: Add structured response format
    Result: PASS ✓
    Score: 0.1234

    Metrics:
      success_rate:
        Baseline: 73.3%
        Candidate: 83.3%
        Delta: +10.0%
      p95_model_latency_ms:
        Baseline: 1245ms
        Candidate: 1312ms
        Delta: +67ms
      avg_cost_usd:
        Baseline: $0.0023
        Candidate: $0.0024
        Delta: +$0.0001

    PASS

--- Phase 6: Validation ---

Validation Results:
  Success rate: 85.7% (was 73.3%)
  P95 latency: 1290ms (was 1245ms)
  Avg cost: $0.0024 (was $0.0023)

  Improvement: +12.4%

  ✓ AutoFlow successfully improved the system!
```

## Key Features Demonstrated

### 1. **Real API Integration**
- Makes actual OpenAI API calls
- Tracks real latency, cost, and token usage

### 2. **Quality Evaluation**
- Heuristics-based quality scoring:
  - Length checks (not too short/long)
  - Structure detection
  - Code example detection
  - Hedging detection
  - Refusal detection

### 3. **Custom Rules**
- `LowQualityRule` analyzes runs and proposes specific improvements:
  - Longer prompts if answers too short
  - Structured prompts if answers unstructured
  - Code-focused prompts if examples missing
  - Confident prompts if too much hedging

### 4. **Replay Simulation**
- Simulates proposed changes on historical data
- Predicts impact on metrics
- Uses domain-specific heuristics for simulation

### 5. **Safety Gates**
- Prevents regressions beyond thresholds
- Requires minimum improvements
- Only applies safe changes

### 6. **End-to-End Validation**
- Confirms improvements on new data
- Demonstrates real-world impact

## Customization

You can customize the demo by modifying:

### Prompt Variants
```python
PROMPT_VARIANTS = [
    PromptConfig(name="baseline", system_prompt="...", temperature=0.7),
    PromptConfig(name="detailed", system_prompt="...", temperature=0.5),
    # Add your own variants
]
```

### Test Questions
```python
TEST_QUESTIONS = [
    "Your question here?",
    # Add more questions
]
```

### Quality Heuristics
Modify `evaluate_answer_quality()` to customize:
- What constitutes quality
- Issue detection logic
- Scoring thresholds

### Safety Gates
```python
gates=ReplayGates(
    max_regressions={
        "p95_model_latency_ms": 200.0,  # Adjust tolerance
        "avg_cost_usd": 0.005,
    },
    min_improvements={
        "success_rate": 0.05,  # Adjust requirement
    },
)
```

## Production Considerations

This demo uses simplified heuristics. In production:

1. **Quality Evaluation**
   - Use LLM-as-judge for more accurate scoring
   - Implement human feedback loops
   - Add automated tests

2. **Replay Simulation**
   - Actually re-run candidate prompts (for critical changes)
   - Use smaller models to approximate
   - Cache responses for speed

3. **Metrics**
   - Add more metrics (relevance, hallucination detection, etc.)
   - Track user satisfaction
   - Monitor for bias

4. **Rules**
   - Add more sophisticated detection logic
   - Implement ML-based pattern detection
   - Add domain-specific rules

## Cost

This demo makes approximately **20-30 OpenAI API calls** using `gpt-4o-mini`.
Estimated cost: **$0.05 - $0.10** per run.

To reduce cost during development:
- Reduce `TEST_QUESTIONS` count
- Test fewer prompt variants
- Use cheaper model (change `gpt-4o-mini` to `gpt-3.5-turbo`)
