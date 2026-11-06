"""Read-only OpenRouter checks; never retain key labels, hashes or raw errors."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx

BASE_URL = 'https://openrouter.ai/api/v1'
MODEL = 'qwen/qwen3.5-9b'


class PreflightError(Exception):
    pass


def _amount(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise PreflightError('invalid_numeric_budget_or_price')
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise PreflightError('invalid_numeric_budget_or_price') from None
    if not result.is_finite() or result < 0:
        raise PreflightError('invalid_numeric_budget_or_price')
    return result


def _get(path, *, key=None, transport=None):
    if transport is not None and not isinstance(transport, httpx.MockTransport):
        raise PreflightError('invalid_test_transport')
    try:
        with httpx.Client(timeout=20, trust_env=False, follow_redirects=False, transport=transport) as client:
            headers = {'Authorization': 'Bearer ' + key.get_secret_value()} if key else {}
            response = client.get(BASE_URL + path, headers=headers)
            if response.status_code != 200:
                raise PreflightError('metadata_request_failed_' + str(response.status_code))
            if len(response.content) > 4_000_000:
                raise PreflightError('metadata_response_too_large')
            data = response.json()['data']
            if not isinstance(data, dict):
                raise PreflightError('malformed_metadata')
            return data
    except PreflightError:
        raise
    except Exception:
        raise PreflightError('metadata_request_failed') from None


def check_model(plan, *, transport=None):
    if plan['model'] != MODEL or plan['base_url'] != BASE_URL:
        raise PreflightError('unapproved_model_or_endpoint')
    data = _get('/models/' + MODEL + '/endpoints', transport=transport)
    if data.get('id') != MODEL:
        raise PreflightError('model_identity_mismatch')
    endpoints = []
    required = {'max_tokens', 'temperature', 'top_p', 'response_format', 'reasoning'}
    for item in data.get('endpoints', []):
        prices = item.get('pricing', {})
        prompt = _amount(prices.get('prompt')) * 1_000_000
        completion = _amount(prices.get('completion')) * 1_000_000
        eligible = (item.get('status') == 0 and required <= set(item.get('supported_parameters', []))
                    and prompt <= _amount(plan['input_usd_per_million'])
                    and completion <= _amount(plan['output_usd_per_million'])
                    and _amount(prices.get('request', 0)) == 0)
        endpoints.append({'provider': item.get('provider_name'), 'status': item.get('status'),
                          'input_usd_per_million': str(prompt), 'output_usd_per_million': str(completion),
                          'eligible_at_approved_limits': eligible})
    if not any(item['eligible_at_approved_limits'] for item in endpoints):
        raise PreflightError('no_available_route_with_approved_options_and_prices')
    return {'checked_utc': datetime.now(timezone.utc).isoformat(), 'model': MODEL,
            'source': BASE_URL + '/models/' + MODEL + '/endpoints', 'endpoints': endpoints,
            'availability_scope': 'Public route listing only; account inference access remains untested.'}


def check_key(key, *, minimum_remaining, require_unused=True, transport=None):
    if not key or not key.get_secret_value().strip():
        raise PreflightError('credential_missing')
    data = _get('/key', key=key, transport=transport)
    limit = _amount(data.get('limit'))
    remaining = _amount(data.get('limit_remaining'))
    usage = _amount(data.get('usage'))
    if limit != Decimal('.10') or data.get('limit_reset', 'missing') is not None:
        raise PreflightError('dedicated_key_requires_010_lifetime_cap')
    if data.get('is_management_key') is True or data.get('is_provisioning_key') is True:
        raise PreflightError('dedicated_inference_key_required')
    if require_unused and (usage != 0 or remaining != limit):
        raise PreflightError('dedicated_unused_key_required')
    if remaining > limit or remaining < _amount(minimum_remaining):
        raise PreflightError('insufficient_or_inconsistent_remaining_budget')
    return {'checked_utc': datetime.now(timezone.utc).isoformat(), 'limit_usd': str(limit),
            'remaining_usd': str(remaining), 'usage_usd': str(usage), 'limit_reset': None,
            'source': BASE_URL + '/key', 'verified': True}
