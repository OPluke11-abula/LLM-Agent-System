---
id: verify_workspace
name: Verify Workspace
description: Run tool sync and contract static analysis validation
version: 1.0.0
steps:
  - step_id: verify_contracts_and_lints
    skill_id: verify_workspace
    params:
      sync_first: true
    next_step: null
---
# Verify Workspace

This declarative workflow automatically synchronizes tool manifests, validates Pydantic model reflections against matching PAP contracts, and runs static path traversal check rules.
It guarantees absolute integrity across all local and global agent skills.
