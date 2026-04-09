# Auto-Tensor: Roadmap

## Phase 1: Foundation (v1.x) [COMPLETED]

- Core agent architecture (Intelligence & Engineering).
- Basic mission intake and dispatch.
- Initial dashboard UI.

## Phase 2: Hardening & Resiliency (v2.x) [IN PROGRESS]

- **Project Memory Ledger**: Established centralized state management.
- **Resilient API Communication**: Implemented robust retry/backoff for LLM calls.
- **Node Sync**: Real-time telemetry between Intelligence and Engineering nodes.
- **Sovereign Gate**: Audit and Publish stages for PR management.

## Phase 3: Autonomous Intelligence & Knowledge Persistence [NEXT]

- **Data Fidelity**: Ensure the full log context from the Intelligence Node is passed to the Engineering Node during promotion.
- **Skill Synthesis**: Implement a 'Skill Writer' tool. After a successful PR, the agent should summarize the technical lesson learned and append it to `SKILLS.md`.
- **AI-Rules Integration**: The agent must check `.ai-rules` before every task to leverage our local 'Knowledge Base' and minimize Gemini API calls.
- **Doc-Sourcing**: Add a skill for the agents to find and ingest relevant coding documentation to ensure technical accuracy.
- **Rate-Limit Mitigation**: Continue refining exponential backoff and prioritize using local 'Skills' over LLM reasoning to stay under limits.

**_ Under Construction _**
