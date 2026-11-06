"""Read-only preflight, never inference; save only allowlisted public/numeric fields."""
from decimal import Decimal
import json
import os
from pathlib import Path
import sys

from dotenv import dotenv_values
from pydantic import SecretStr

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_hackathon.openrouter_preflight import check_key,check_model,PreflightError
from rag_hackathon.live_evaluation import plan_estimate


def main():
    plan=json.loads((ROOT/'config/phase3_live_plan.json').read_text())
    private=dotenv_values(ROOT/'.env') if (ROOT/'.env').is_file() else {}
    key=SecretStr(os.environ.get('OPENROUTER_API_KEY') or private.get('OPENROUTER_API_KEY') or '')
    result={'authorization':'two smoke attempts only, conditional on secure key and verified cap',
            'maximum_inference_attempts_this_stage':2,'remaining_evaluation_authorized':False,
            'credential_present':bool(key.get_secret_value().strip()),'key_cap_verified':False,
            'live_inference_attempts':0,'stage_inference_spend_usd':'0',
            'provider_reported_remaining_budget_usd':None,
            'two_call_upper_cost_estimate_usd':str(Decimal(plan_estimate(plan)['per_call_upper_estimate_usd'])*2)}
    try:
        result['model_check']=check_model(plan)
        if result['credential_present']:
            result['key_check']=check_key(key,minimum_remaining=result['two_call_upper_cost_estimate_usd'])
            result['key_cap_verified']=True
            result['provider_reported_remaining_budget_usd']=result['key_check']['remaining_usd']
            result['status']='preflight_passed_no_inference_executed'
        else:
            result['status']='waiting_for_private_key_configuration'
    except PreflightError as error:
        result['status']='blocked'
        result['safe_error']=str(error)
    (ROOT/'docs/evidence/phase3_smoke_preflight.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
