"""OPT-IN local model demonstration. No server requests until invoked by user."""
import argparse
import json
from truth_accountability import (
    GovernedTruthCore, GovernedModelBridge, LocalOllamaProposalClient,
    VerificationRegistry, VerifierSpec, bounded_arithmetic, arithmetic_only_policy,
)


def main():
    parser=argparse.ArgumentParser(description="Offline-first local Ollama + governed proposal gate")
    parser.add_argument("--model",required=True,help="Name of model already installed in local Ollama")
    parser.add_argument("--text",required=True,help="Exact source statement for the local test")
    parser.add_argument("--database",default="truth-accountability-local.sqlite3")
    args=parser.parse_args()
    registry=VerificationRegistry()
    registry.register(VerifierSpec("arithmetic","arithmetic-check-v1",bounded_arithmetic))
    core=GovernedTruthCore(args.database,registry)
    try:
        source_id=core.preserve("local-operator",args.text)
        model=LocalOllamaProposalClient(model=args.model)
        proposal=model.generate_proposal(source_id,args.text)
        response=GovernedModelBridge(core,arithmetic_only_policy).process(
            proposal,current_source_id=source_id
        )
        print(json.dumps({"status":response.decision,"reply":response.text,
                          "fact_supported":response.established_fact,
                          "delivery_confirmed":response.verified_delivery},ensure_ascii=False,indent=2))
    finally:
        core.close()

if __name__=="__main__":
    main()
