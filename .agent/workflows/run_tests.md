---
id: run_tests
name: Run pytest Suite
description: Automatically execute the entire pytest suite for FindAi Studio LLM Agent System
version: 1.0.0
steps:
  - step_id: run_pytest_tests
    skill_id: run_tests
    params:
      verbose: true
    next_step: null
---
# Run pytest Suite

This declarative workflow automatically triggers the `run_tests` system skill to execute all 85+ pytests in the repository.
It ensures that all system components, engines, routing concurrent sessions, dynamic RBAC authorization gates, and TF-IDF search fallbacks are verified green.
