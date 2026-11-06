"""Offline-only configuration audit. No inference, model lookup or billing API call."""
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_hackathon.generation.providers import ProviderConfig,ProviderError,load_provider_environment


def audit(env, *, private_file_exists):
    valid=False
    if env.get('LLM_PROVIDER')=='groq':
        try:
            ProviderConfig.from_env(env)
            valid=True
        except ProviderError:
            pass
    flags={'private_env_file_exists':private_file_exists,
           'selected_provider_is_groq':env.get('LLM_PROVIDER')=='groq',
           'groq_credential_present':bool(env.get('GROQ_API_KEY','').strip()),
           'selected_model_matches_reviewed_model':env.get('GROQ_MODEL')=='openai/gpt-oss-120b',
           'groq_configuration_valid':valid,
           'paid_calls_disabled':env.get('ALLOW_PAID_API_CALLS','false').lower()=='false',
           'free_plan_asserted_by_operator':env.get('GROQ_FREE_PLAN_CONFIRMED','false').lower()=='true',
           'free_calls_enabled_by_operator':env.get('ALLOW_FREE_API_CALLS','false').lower()=='true'}
    return {'checks':{key:'PASS' if value else 'FAIL' for key,value in flags.items()},
            'local_configuration_ready':all(value for key,value in flags.items() if key!='private_env_file_exists'),
            'account_free_plan_independently_verified':False,
            'account_verification_status':'FAIL - not verifiable through this offline audit; confirm in Groq Console',
            'inference_authorized_this_turn':False,'live_inference_attempts':0,
            'live_connection_status':'not tested','actual_spend_this_turn_usd':'0',
            'credential_values_in_report':False}


def main():
    private=ROOT/'.env'
    with patch('socket.socket.connect',side_effect=RuntimeError('Offline configuration audit')):
        env=load_provider_environment(private) if private.is_file() else dict(os.environ)
        result=audit(env,private_file_exists=private.is_file())
    path=ROOT/'docs/evidence/groq_configuration_audit.json'
    path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
