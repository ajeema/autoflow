# AutoFlow API Schemas

This document provides the schema definitions for all AutoFlow data models.

---

## Observation Event

An event captured during AutoFlow operation

### Fields

- `event_id` 
  - Unique event identifier
  - **Type:** Event Id

- `timestamp` 
  - Event timestamp (UTC)
  - **Type:** Timestamp

- `source` **(required)**
  - Source of the event (e.g., component name)
  - **Type:** Source

- `name` **(required)**
  - Event name
  - **Type:** Name

- `attributes` 
  - Additional event attributes
  - **Type:** Attributes

---

## Graph Node

A node in the context graph

### Fields

- `node_id` **(required)**
  - Unique node identifier
  - **Type:** Node Id

- `node_type` **(required)**
  - Type of the node
  - **Type:** Node Type

- `properties` 
  - Node properties
  - **Type:** Properties

---

## Graph Edge

An edge in the context graph

### Fields

- `edge_type` **(required)**
  - Type of the edge
  - **Type:** Edge Type

- `from_node_id` **(required)**
  - Source node ID
  - **Type:** From Node Id

- `to_node_id` **(required)**
  - Target node ID
  - **Type:** To Node Id

- `properties` 
  - Edge properties
  - **Type:** Properties

---

## Context Graph Delta

Changes to apply to the context graph

### Fields

- `nodes` 
  - Nodes in this delta
  - **Type:** Nodes

- `edges` 
  - Edges in this delta
  - **Type:** Edges

---

## Change Proposal

A proposed change to the codebase

### Fields

- `proposal_id` 
  - Unique proposal identifier
  - **Type:** Proposal Id

- `kind` **(required)**
  - Type of change
  - **Type:** Kind

- `title` **(required)**
  - Brief title of the proposal
  - **Type:** Title

- `description` **(required)**
  - Detailed description of the change
  - **Type:** Description

- `risk` **(required)**
  - Risk level of this change
  - **Type:** Risk

- `target_paths` 
  - Files/directories affected
  - **Type:** Target Paths

- `payload` 
  - Change-specific data
  - **Type:** Payload

---

## Evaluation Result

Result of evaluating a change proposal

### Fields

- `proposal_id` **(required)**
  - ID of the evaluated proposal
  - **Type:** Proposal Id

- `passed` **(required)**
  - Whether the proposal passed evaluation
  - **Type:** Passed

- `score` **(required)**
  - Evaluation score (can be negative or greater than 1)
  - **Type:** Score

- `metrics` 
  - Detailed metrics
  - **Type:** Metrics

- `notes` 
  - Additional notes or explanation
  - **Type:** Notes

---

## Workflow Step

A single step in a workflow

### Fields

- `step_id` 
  - Unique step identifier
  - **Type:** Step Id

- `name` **(required)**
  - Step name
  - **Type:** Name

- `status` 
  - Step status

- `started_at` 
  - Step start time
  - **Type:** Started At

- `completed_at` 
  - Step completion time
  - **Type:** Completed At

- `error_message` 
  - Error message if failed
  - **Type:** Error Message

- `metadata` 
  - Additional step metadata
  - **Type:** Metadata

---

## Workflow Execution

A complete workflow execution

### Fields

- `workflow_id` 
  - Unique workflow identifier
  - **Type:** Workflow Id

- `name` **(required)**
  - Workflow name
  - **Type:** Name

- `started_at` 
  - Workflow start time
  - **Type:** Started At

- `completed_at` 
  - Workflow completion time
  - **Type:** Completed At

- `status` 
  - Overall workflow status

- `steps` 
  - Workflow steps
  - **Type:** Steps

- `metadata` 
  - Additional metadata
  - **Type:** Metadata

---

## Context Source

A source of context information

### Fields

- `source_id` **(required)**
  - Unique source identifier
  - **Type:** Source Id

- `source_type` **(required)**
  - Type of context source
  - **Type:** Source Type

- `enabled` 
  - Whether this source is enabled
  - **Type:** Enabled

- `config` 
  - Source-specific configuration
  - **Type:** Config

- `priority` 
  - Source priority (higher = preferred)
  - **Type:** Priority

---
