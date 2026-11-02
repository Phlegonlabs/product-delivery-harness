<!-- Copy "## Migration and Cutover" into docs/product/architecture.md after "## Deployment and Operations". Copy the TEST-MIG rows into the "## Test Obligations" table of docs/product/PRD.md, with a Must requirement PRD-PRG-<NNN> for the migration. Copy "### Migration" into each module's docs/product/modules/<module-id>/architecture.md under "## Deployment and Operations", using that module's scope in its IDs. Replace every [bracket] and <angle> placeholder, then delete this comment. A greenfield program writes "not_required — <reason>" under "## Migration and Cutover" and skips the rest. -->
## Migration and Cutover
### Legacy Sources
| ARCH ID | Legacy source | Owner | Extract method | Volume | Target module |
| --- | --- | --- | --- | --- | --- |
| ARCH-MIG-001 | [System, file or spreadsheet that holds the data today] | [Human owner] | [Export, query, API or manual] | [Rows or GB] | [module-id] |

### Mapping and Reconciliation
| ARCH ID | Legacy field | Target entity.field | Transform | Control total | TEST IDs |
| --- | --- | --- | --- | --- | --- |
| ARCH-MIG-002 | [Legacy field] | [entity.field] | [Rule, or copy] | [Count or sum that must match] | TEST-MIG-001, TEST-MIG-002 |

### Parallel Run and Cutover
| Step | When | Action | Owner | Go / no-go signal | Rollback |
| --- | --- | --- | --- | --- | --- |
| [Step] | [Date or relative time] | [Action] | [Human owner] | [Observable signal] | [How to go back] |

<!-- TEST-MIG rows for the program PRD -->
| TEST ID | Obligation | Test type | Required | Upstream trace IDs | Expected signal |
| --- | --- | --- | --- | --- | --- |
| TEST-MIG-001 | Dress rehearsal on a copy of the legacy data | operational | Yes | PRD-PRG-<NNN> | Every control total in Mapping and Reconciliation matches |
| TEST-MIG-002 | Re-run of the load | integration | Yes | PRD-PRG-<NNN> | The second load adds 0 rows and every control total is unchanged |
| TEST-MIG-003 | Parallel run of [N] cycles | operational | Yes | PRD-PRG-<NNN> | Legacy and new outputs differ only in rows listed in the explained-differences log |
| TEST-MIG-004 | Rollback rehearsal | operational | Yes | PRD-PRG-<NNN> | The legacy system is restored within [time] and its control totals equal the pre-cutover snapshot |

### Migration
| ARCH ID | Legacy field | Target entity.field | Transform | Control total | TEST IDs |
| --- | --- | --- | --- | --- | --- |
| ARCH-<SCOPE>-<NNN> | [Legacy field this module's data comes from] | [entity.field] | [Rule, or copy] | [Count or sum that must match] | TEST-<SCOPE>-<NNN> |
