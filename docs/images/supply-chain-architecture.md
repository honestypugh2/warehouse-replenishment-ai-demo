# Warehouse Replenishment AI — Architecture

This diagram represents the end-to-end warehouse replenishment architecture spanning Databricks (system of intelligence), Microsoft 365 Copilot (hub), and Microsoft Foundry (reasoning engine), with D365 F&O as the system of record.

## Architecture Diagram (Mermaid)

```mermaid
graph TB
    subgraph Databricks["Databricks - System of Intelligence"]
        direction TB
        MME["Min-Max Candidate Engine"]
        VH["Velocity and History Analysis"]
        DSQL[Databricks SQL]
        DSQL --> MME
        VH --> MME
    end

    subgraph DataFoundation["Warehouse Data Foundation"]
        direction LR
        CAND[Candidates]
        INV[SKU Inventory]
        ORD[Open Orders]
        WAV[Waves]
        CAP[Capacity]
    end

    subgraph M365["Microsoft 365 Copilot"]
        direction TB
        subgraph CS["Copilot Studio - Hub"]
            RA["Replenishment Assistant"]
            TOP["Topics and Flows"]
        end
    end

    subgraph Teams["Teams Channel"]
        direction LR
        AC[Approval Cards]
        RC[Rejection Cards]
        CONV["Planner Conversations"]
    end

    subgraph Backend["⚡ FastAPI Backend"]
        direction LR
        RSEQ["recommendations/sequential"]
        RVAL["validate"]
        RAPP["approve"]
    end

    subgraph Foundry["Microsoft Foundry - Reasoning Engine"]
        direction TB
        subgraph AgentFW["Agent Framework - Sequential Orchestration"]
            RET[Retriever Agent]
            VAL[Validator Agent]
            REC[Recommender Agent]
        end
        AOAI["Azure OpenAI gpt-4o"]
        AI[Application Insights]
    end

    subgraph D365["D365 F and O - System of Record"]
        MMP["Min-Max Parameters"]
        OO["Open Orders and Wave Status"]
    end

    %% Data flow connections
    DataFoundation -.-> Databricks
    Teams -.-> CS
    Backend -.-> CS
    M365 <-.-> Foundry
    Databricks <-.-> Foundry
    D365 <-.-> Foundry
    AOAI -.-> AgentFW
    AI -.-> Foundry
    Backend -.-> Foundry
```

## Component Summary

| Platform | Components | Role |
|----------|-----------|------|
| **Databricks** | Min-Max Candidate Engine, Velocity & History Analysis, Databricks SQL | System of intelligence — daily min-max candidate logic and demand analysis |
| **Warehouse Data** | Candidates, SKU Inventory, Open Orders, Waves, Capacity | Operational data foundation for replenishment decisions |
| **Microsoft 365 Copilot** | Copilot Studio (Replenishment Assistant), Topics & Flows | Business-user entry point, orchestration hub, Teams publishing |
| **Teams** | Approval Cards, Rejection Cards, Planner Conversations | Human-in-the-loop approval and notification channel |
| **FastAPI Backend** | /recommendations/sequential, /validate, /approve | REST API bridge between Copilot Studio and Foundry workflows |
| **Microsoft Foundry** | Agent Framework (Retriever → Validator → Recommender), Azure OpenAI (gpt-4o), Application Insights | AI reasoning engine, agent orchestration, observability |
| **D365 F&O** | Min-Max Parameters, Open Orders & Wave Status | System of record — the only place writes are executed |

## Data Flow

1. **Warehouse data** (candidates, SKU inventory, orders, waves, capacity) feeds into **Databricks** for min-max candidate analysis
2. **Databricks** computes daily candidates with velocity, confidence scores, and rationale
3. **Copilot Studio** acts as the hub — the Replenishment Assistant routes user intent to the right tool
4. **FastAPI Backend** exposes `/recommendations/sequential`, `/validate`, and `/approve` as REST tools for Copilot Studio
5. **Microsoft Foundry's Agent Framework** runs the sequential pipeline: Retriever → Validator → Recommender, powered by **Azure OpenAI (gpt-4o)**
6. The **Validator Agent** cross-references D365 open orders and wave status to flag blocked SKUs
7. **Approval cards** surface in Teams; only explicit human approval triggers the **D365 write** path
8. **Application Insights** traces every agent invocation for auditability
