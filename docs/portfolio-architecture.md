# Portfolio architecture and data flows

Every project is an isolated, dependency-free Python demonstration. Inputs are synthetic files checked into that project's `data/` directory. Generated databases, reports, manifests, and lakehouse layers are ignored by Git.

## 01 — Enterprise data integration

```mermaid
flowchart LR
    C[customers.csv] --> V[Header and customer validation]
    O[orders.csv] --> V
    V --> J[Join and normalize]
    J --> G[customer_orders.csv]
    V --> Q[rejected_orders.csv]
```

## 02 — Financial and insurance analytics

```mermaid
flowchart LR
    P[policies.csv] --> L[SQLite loader]
    T[payments.csv] --> L
    C[commissions.csv] --> L
    L --> S[Parameterized aggregate SQL]
    S --> R[reconciliation.csv]
    L --> D[reconciliation.db]
```

## 03 — Healthcare interoperability

```mermaid
flowchart LR
    H[HL7 v2 ORU sample] --> HP[OBX parser]
    F[FHIR R4 Bundle sample] --> FP[Observation parser]
    HP --> N[Canonical observation validation]
    FP --> N
    N --> O[normalized_observations.csv]
```

## 04 — Cloud modernization and DataOps

```mermaid
flowchart LR
    I[events.csv] --> B[Bronze: immutable source copy]
    B --> V[Validate, type, and quarantine]
    V --> S[Silver: clean_events.csv]
    S --> G[Gold: SQL daily summary]
    B --> M[Run manifest and SHA-256]
    V --> M
```

## Class diagrams

### Enterprise integration

```mermaid
classDiagram
    class CsvReader {
        +read(path, required_headers)
    }
    class IntegrationPipeline {
        +run(customers, orders)
        +validate_order(row)
        +join_customer(row)
    }
    class OutputWriter {
        +write_rows(path, rows)
    }
    IntegrationPipeline --> CsvReader
    IntegrationPipeline --> OutputWriter
```

### Financial reconciliation

```mermaid
classDiagram
    class ReconciliationJob {
        +run(policies, payments, commissions, database)
    }
    class SqliteWarehouse {
        +initialize(connection)
        +load(connection, input_rows)
        +reconcile(connection)
    }
    class CsvReport {
        +write(path, rows)
    }
    ReconciliationJob --> SqliteWarehouse
    ReconciliationJob --> CsvReport
```

### Healthcare interoperability

```mermaid
classDiagram
    class InteroperabilityPipeline {
        +run(hl7_path, fhir_path, output_path)
    }
    class Hl7OrUParser {
        +parse(text)
    }
    class FhirBundleParser {
        +parse(bundle)
    }
    class ObservationWriter {
        +write(path, observations)
    }
    InteroperabilityPipeline --> Hl7OrUParser
    InteroperabilityPipeline --> FhirBundleParser
    InteroperabilityPipeline --> ObservationWriter
```

### DataOps

```mermaid
classDiagram
    class MedallionPipeline {
        +run(input_path, lakehouse_dir)
        +validate(row)
        +summarize(rows)
    }
    class LayerWriter {
        +write_bronze(path, content)
        +write_csv(path, rows)
        +write_manifest(path, metadata)
    }
    MedallionPipeline --> LayerWriter
```
