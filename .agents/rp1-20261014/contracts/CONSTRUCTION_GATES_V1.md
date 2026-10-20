# Construction order and gate acceptance v1

Status: IMPLEMENTED_NOT_QUALIFIED. `src/ceta/contracts/construction.py` is a pure source-bound model. It neither changes work-package/gate ledgers nor permits runtime kickoff, profile activation, cutover or publication.

| Source input | Exact authorized path | SHA-256 |
| --- | --- | --- |
| Full package graph | T:\00-Active\CETA_Intelligence_Operating_System_Build_Package\build\work_packages.json | 2b573de7550336aae7c671e69bb49fa9011889513fec792967f0ed3286819017 |
| Eight formal gates | T:\00-Active\CETA_Intelligence_Operating_System_Build_Package\build\gates.json | 04afba11afa8a707ac70651d2ef26efed65d75b0d6d6edde44c2399c2a36848b |

Construct `ConstructionPlan(work_package_bytes, gate_bytes)` with these exact inputs. Different bytes require a reviewed model/version update. The model retains all package fields, including parents, original acceptance IDs, owners, status and evidence refs; it retains every gate name, member, acceptance body, recorded state and evidence ref. It checks full IDs WP-00 through WP-27 and G-A through G-H, unique coverage and target-gate agreement.

## Deterministic interpretation

A dependency is a construction prerequisite. A target gate is the acceptance group that must qualify that package and all applicable non-package duties. The graph does not say that every package labeled with a later letter must wait for formal qualification of each earlier letter. Treating letters as construction barriers adds an unsupported dependency and creates the apparent WP-16/WP-15 and WP-21/WP-18 deadlocks.

REQ-39-02 at docs/specification/39_implementation_and_coordination.md:14 (SHA3886233cad7a26011bb58459997dbf32a32f818f7b0149da4ce382dc7c415b2f) directs building and extending the same real cycle, with required controls before exposed effects. REQ-41-01/02/04 at docs/specification/41_completion_gates.md:10/14/22 (SHA7d8b49da2cd4c53e480bda590433bd36c1b58a4d7a0fd86a4e821774100ef7b3) separately require full gate evidence and rechecking earlier guarantees. This source-based construction interpretation changes no graph edge, membership, acceptance condition, or activation control.

| Package | Exact construction prerequisites | Unchanged target gate |
| --- | --- | --- |
| WP-00 | none | G-A |
| WP-01 | WP-00 | G-A |
| WP-02 | WP-01 | G-B |
| WP-03 | WP-02 | G-B |
| WP-04 | WP-03 | G-B |
| WP-05 | WP-04 | G-B |
| WP-06 | WP-05 | G-C |
| WP-07 | WP-06 | G-C |
| WP-08 | WP-06 | G-C |
| WP-09 | WP-07 WP-08 | G-C |
| WP-10 | WP-09 | G-C |
| WP-11 | WP-10 | G-C |
| WP-12 | WP-11 | G-C |
| WP-13 | WP-04 | G-D |
| WP-14 | WP-13 WP-03 | G-D |
| WP-15 | WP-12 WP-13 | G-D |
| WP-16 | WP-12 WP-15 | G-C |
| WP-17 | WP-16 | G-E |
| WP-18 | WP-09 WP-12 WP-16 | G-F |
| WP-19 | WP-16 WP-18 | G-F |
| WP-20 | WP-16 WP-12 | G-D |
| WP-21 | WP-18 | G-D |
| WP-22 | WP-12 WP-17 WP-19 | G-F |
| WP-23 | WP-17 WP-19 WP-22 | G-F |
| WP-24 | WP-23 | G-F |
| WP-25 | WP-24 | G-G |
| WP-26 | WP-14 WP-20 WP-22 | G-G |
| WP-27 | WP-25 WP-26 | G-H |

`topological_order` chooses the lexically smallest ready ID on each iteration. It is deterministic across input ordering and rejects duplicate nodes/dependencies, unknown references, malformed/boundedness violations, self-cycles and multi-node cycles. The full graph is acyclic. WP-15 must precede WP-16 even though their targets are D and C. WP-18 must precede WP-21 even though their targets are F and D.

`construction_ready(completed_packages)` uses only supplied completion claims and dependencies; claims must themselves be dependency-closed. A claim that WP-16 or WP-21 is completed without its prerequisites rejects. Readiness is not a kernel authorization or proof that a package is implemented/qualified. Gate A's source/full-contract conditions still control real runtime kickoff.

## Exact gate membership and acceptance

| Gate | Unchanged member packages |
| --- | --- |
| G-A | WP-00 WP-01 |
| G-B | WP-02 WP-03 WP-04 WP-05 |
| G-C | WP-06 WP-07 WP-08 WP-09 WP-10 WP-11 WP-12 WP-16 |
| G-D | WP-13 WP-14 WP-15 WP-20 WP-21 |
| G-E | WP-17 |
| G-F | WP-18 WP-19 WP-22 WP-23 WP-24 |
| G-G | WP-25 WP-26 |
| G-H | WP-27 |

`assess_gate` returns the exact member list, transitive package prerequisite closure, missing members, missing dependencies, and exact acceptance body. Member completion alone cannot satisfy missing prerequisites or the gate's actual evidence conditions. G-C's checklist includes WP-15 through WP-16; G-D's checklist includes WP-18 through WP-21. No relabeling is needed.

`acceptance_evidence_verified` and evidence references are unauthenticated caller claims. The leaf validates their shape and presence only. Even an all-positive fixture returns gate_qualified=false and runtime_authorized=false. It does not establish real source reconciliation, restoration, independent observation, OS isolation, installed offline bytes, elapsed endurance, custody, physical hardware, or owner cutover. Existing formal states and evidence remain untouched.

All later gates must recheck applicable earlier guarantees (REQ-41-02). The model's package closure does not replace that separate semantic acceptance duty. Before exposing an effect, every required control must operate (REQ-39-02). Mandatory unavailable lanes remain open; disabling them does not complete the full mission (REQ-41-04).

## Validation and limits

`tests/contract/test_construction.py` loads the exact supplied 28/8 inputs from the expressly authorized sibling build package. It checks every original package/gate field, all dependency ordering, deterministic reversal, full construction readiness, cross-gate edges, incoherent claims, each omitted prerequisite/member, evidence absence, source drift, cycles/duplicates/malformed inputs and immutable source preservation.

The original cases B001/B008/B045/B053/B054 and B121/B127/B128 remain NOT_RUN; these source fixtures do not qualify those scenarios. Full 175 requirements, 25 components, 128 original cases, 28 packages and eight gates remain in scope. Gate A remains OPEN and all formal gates remain NOT_EVALUATED.

