# AI SQL Bot — Mermaid Diagrams

> GitHub renders Mermaid code blocks in Markdown automatically. Just commit this file to your repo (e.g., `docs/diagrams.md` or your `README.md`).

## 1. Project Structure

```mermaid
flowchart LR
    A[ai-sql-bot/]:::root

    subgraph FRONTEND[frontend/]
      FE1[layout.py]
      FE2[components.py]
      FE3[callbacks.py]
    end

    subgraph BACKEND[backend/]
      B1[planner.py]
      B2[retriever.py]
      B3[sql_generator.py]
      B4[validator.py]
      B5[executor.py]
      B6[summarizer.py]
      B7[pipeline.py]
    end

    subgraph DB[db/]
      D1[schema.sql]
      D2[sample_data.sql]
      D3[setup_db.py]
      D4[db_utils.py]
    end

    subgraph VS[vectorstore/]
      V1[chroma_store.py]
      V2[embedder.py]
    end

    subgraph TESTS[tests/]
      T1[test_planner.py]
      T2[test_sql_generator.py]
      T3[test_validator.py]
      T4[test_executor.py]
      T5[test_summarizer.py]
      T6[test_pipeline.py]
    end

    subgraph DOCS[docs/]
      X1[architecture.md]
      X2[challenges.md]
      X3[performance.md]
      X4[demo_instructions.md]
    end

    subgraph ARTIFACTS[artifacts/]
      Y1[demo_video.mp4]
      Y2[screenshots/]
    end

    A --> FRONTEND
    A --> BACKEND
    A --> DB
    A --> VS
    A --> TESTS
    A --> DOCS
    A --> ARTIFACTS
    A --> Z1[app.py]
    A --> Z2[pyproject.toml]
    A --> Z3[requirements.txt]
    A --> Z4[README.md]
    A --> Z5[.env.example]
    A --> Z6[.gitignore]

    classDef root fill:#222,color:#fff,stroke:#555,stroke-width:1.5px;
```

## 2. High-level Architecture

```mermaid
flowchart LR
    User((User))
    UI[Streamlit UI<br/>app.py + frontend/*]
    Pipeline[pipeline.py<br/>Orchestrator]
    Planner[planner.py]
    Retriever[retriever.py]
    Chroma[(ChromaDB<br/>vectorstore/chroma_store.py)]
    Embedder[Embeddings<br/>vectorstore/embedder.py]
    SQLGen[sql_generator.py]
    Validator[validator.py]
    Executor[executor.py]
    SQLite[(SQLite DB<br/>db/*.sql, db_utils.py)]
    Summarizer[summarizer.py]

    User --> UI --> Pipeline
    Pipeline --> Planner
    Pipeline --> Retriever
    Retriever --> Chroma
    Retriever -.uses.-> Embedder
    Pipeline --> SQLGen
    SQLGen --> Validator
    Validator -->|safe| Executor --> SQLite
    Executor --> Pipeline
    Pipeline --> Summarizer --> UI
    Validator -.blocked/rewritten.-> Pipeline
```

## 3. Agentic Workflow (Sequence)

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant S as Streamlit UI
    participant P as pipeline.py
    participant PL as planner.py
    participant R as retriever.py
    participant C as ChromaDB
    participant G as sql_generator.py
    participant V as validator.py
    participant E as executor.py
    participant DB as SQLite
    participant SU as summarizer.py

    U->>S: Natural language question
    S->>P: on_submit(query)
    P->>PL: Plan steps / clarify schema needs
    PL-->>P: Plan (intent, entities, tables)
    P->>R: Retrieve schema/context chunks
    R->>C: similarity_search()
    C-->>R: top-k docs (DDL, samples)
    R-->>P: context
    P->>G: Generate SQL with context+plan
    G-->>P: SQL string
    P->>V: Static checks, allowlist, sandboxing
    alt SQL unsafe
        V-->>P: Blocked (reason + fix hints)
        P-->>S: Show warning & suggested rewrite
        Note over S: User can accept rewrite or edit
    else SQL safe
        V-->>P: Approved
        P->>E: Execute(query, params)
        E->>DB: run (read-only tx)
        DB-->>E: rows / error
        E-->>P: result set
        P->>SU: Summarize + chart hints
        SU-->>S: Natural language answer + table/plot
    end
```

## 4. SQL Safety Checks

```mermaid
flowchart TD
    A[Proposed SQL] --> B{Contains write ops?}
    B -- Yes --> X[Reject / require override]
    B -- No --> C{Access only known tables/cols?}
    C -- No --> X
    C -- Yes --> D{Regex/AST forbidden patterns<br/>(; DROP, PRAGMA, ATTACH, DETACH,<br/> ;-, --, /* */ in risky spots)}
    D -- Fail --> X
    D -- Pass --> E{Query complexity limits<br/>(row caps, timeouts, joins)}
    E -- Exceeds --> X
    E -- OK --> F[Approve for execution]
```

## 5. Test Coverage Map

```mermaid
flowchart LR
    TP[test_planner.py] --> planner.py
    TG[test_sql_generator.py] --> sql_generator.py
    TV[test_validator.py] --> validator.py
    TE[test_executor.py] --> executor.py
    TS[test_summarizer.py] --> summarizer.py
    TPi[test_pipeline.py] --> pipeline.py
```

## 6. Demo Run Path

```mermaid
flowchart LR
    start([Start app.py]) --> S1[Load .env / config]
    S1 --> S2[Init vectorstore + embeddings]
    S2 --> S3[Ensure SQLite setup_db.py ran]
    S3 --> UI[Render Streamlit UI]
    UI --> Q{User asks a question}
    Q -->|submit| P[pipeline.run()]
    P --> OUT[Answer + table + optional chart]
    OUT --> end([Done])
```
