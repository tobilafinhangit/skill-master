#!/usr/bin/env python3
"""
API Parity Verification Script
Compares responses between a Source and Target API based on a manifest.
"""

import argparse
import json
import os
import re
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def load_env_file(env_path: str) -> dict:
    """Load environment variables from a .env file."""
    env_vars = {}
    if env_path and os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars


def substitute_vars(obj, env_vars: dict):
    """Recursively substitute {{VAR}} placeholders in strings."""
    if isinstance(obj, str):
        def replacer(match):
            var_name = match.group(1)
            return env_vars.get(var_name, os.environ.get(var_name, match.group(0)))
        return re.sub(r'\{\{(\w+)\}\}', replacer, obj)
    elif isinstance(obj, dict):
        return {k: substitute_vars(v, env_vars) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [substitute_vars(item, env_vars) for item in obj]
    return obj


def make_request(base_url: str, endpoint: str, method: str, headers: dict, body: dict = None) -> tuple:
    """Make an HTTP request and return (status_code, response_body, error)."""
    url = base_url.rstrip('/') + '/' + endpoint.lstrip('/')
    headers = headers or {}
    headers.setdefault('Content-Type', 'application/json')
    headers.setdefault('Accept', 'application/json')
    
    data = None
    if body:
        data = json.dumps(body).encode('utf-8')
    
    try:
        req = Request(url, data=data, headers=headers, method=method)
        with urlopen(req, timeout=30) as response:
            body_text = response.read().decode('utf-8')
            try:
                body_json = json.loads(body_text)
            except json.JSONDecodeError:
                body_json = body_text
            return response.status, body_json, None
    except HTTPError as e:
        try:
            body_text = e.read().decode('utf-8')
            body_json = json.loads(body_text)
        except:
            body_json = str(e)
        return e.code, body_json, None
    except URLError as e:
        return None, None, str(e.reason)
    except Exception as e:
        return None, None, str(e)


def check_body_contains(body, expected_keys: list) -> list:
    """Check if body contains expected keys. Returns list of missing keys."""
    if not isinstance(body, dict):
        return expected_keys
    missing = []
    for key in expected_keys:
        if key not in body:
            missing.append(key)
    return missing


def run_verification(source_url: str, target_url: str, manifest: list, env_vars: dict) -> list:
    """Run all verification tests and return results."""
    results = []
    
    for test in manifest:
        test = substitute_vars(test, env_vars)
        name = test.get('name', 'Unnamed Test')
        endpoint = test.get('endpoint', '/')
        method = test.get('method', 'GET').upper()
        headers = test.get('headers', {})
        body = test.get('body')
        expected_status = test.get('expected_status')
        expected_body_contains = test.get('expected_body_contains', [])
        
        result = {
            'name': name,
            'endpoint': endpoint,
            'method': method,
            'status': 'PASS',
            'notes': []
        }
        
        # Make target request
        target_status, target_body, target_error = make_request(
            target_url, endpoint, method, headers.copy(), body
        )
        
        if target_error:
            result['status'] = 'FAIL'
            result['notes'].append(f"Target error: {target_error}")
            results.append(result)
            continue
        
        result['target_status'] = target_status
        
        # Check expected status
        if expected_status and target_status != expected_status:
            result['status'] = 'FAIL'
            result['notes'].append(f"Expected status {expected_status}, got {target_status}")
        
        # Check expected body keys
        if expected_body_contains:
            missing = check_body_contains(target_body, expected_body_contains)
            if missing:
                result['status'] = 'FAIL'
                result['notes'].append(f"Missing keys in response: {missing}")
        
        # Compare with source if provided
        if source_url:
            source_status, source_body, source_error = make_request(
                source_url, endpoint, method, headers.copy(), body
            )
            
            if source_error:
                result['notes'].append(f"Source error (skipped comparison): {source_error}")
            else:
                result['source_status'] = source_status
                
                if source_status != target_status:
                    result['status'] = 'DIFF'
                    result['notes'].append(f"Status diff: Source={source_status}, Target={target_status}")
                
                # Simple body comparison (keys only for objects)
                if isinstance(source_body, dict) and isinstance(target_body, dict):
                    source_keys = set(source_body.keys())
                    target_keys = set(target_body.keys())
                    
                    missing_in_target = source_keys - target_keys
                    extra_in_target = target_keys - source_keys
                    
                    if missing_in_target:
                        if result['status'] == 'PASS':
                            result['status'] = 'DIFF'
                        result['notes'].append(f"Keys missing in target: {list(missing_in_target)}")
                    
                    if extra_in_target:
                        result['notes'].append(f"Extra keys in target: {list(extra_in_target)}")
        
        results.append(result)
    
    return results


def print_results(results: list, source_url: str, target_url: str):
    """Print results as markdown."""
    print("\n# API Verification Results\n")
    print(f"**Source**: {source_url or 'N/A'}")
    print(f"**Target**: {target_url}\n")
    
    # Summary
    pass_count = sum(1 for r in results if r['status'] == 'PASS')
    diff_count = sum(1 for r in results if r['status'] == 'DIFF')
    fail_count = sum(1 for r in results if r['status'] == 'FAIL')
    
    print(f"## Summary")
    print(f"- ✅ **PASS**: {pass_count}")
    print(f"- ⚠️ **DIFF**: {diff_count}")
    print(f"- ❌ **FAIL**: {fail_count}")
    print()
    
    # Detailed results
    print("## Detailed Results\n")
    print("| Status | Test | Method | Endpoint | Notes |")
    print("|--------|------|--------|----------|-------|")
    
    status_icons = {'PASS': '✅', 'DIFF': '⚠️', 'FAIL': '❌'}
    
    for r in results:
        icon = status_icons.get(r['status'], '❓')
        notes = '; '.join(r['notes']) if r['notes'] else '-'
        print(f"| {icon} {r['status']} | {r['name']} | {r['method']} | `{r['endpoint']}` | {notes} |")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Verify API parity between Source and Target APIs',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--source', help='Base URL of the source API (optional)')
    parser.add_argument('--target', required=True, help='Base URL of the target API')
    parser.add_argument('--manifest', required=True, help='Path to verification manifest JSON')
    parser.add_argument('--env-file', help='Path to .env file for variable substitution')
    
    args = parser.parse_args()
    
    # Load manifest
    try:
        with open(args.manifest, 'r') as f:
            manifest = json.load(f)
    except FileNotFoundError:
        print(f"Error: Manifest file not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in manifest: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Load env vars
    env_vars = load_env_file(args.env_file)
    
    # Run verification
    results = run_verification(args.source, args.target, manifest, env_vars)
    
    # Print results
    print_results(results, args.source, args.target)
    
    # Exit with error code if any failures
    if any(r['status'] == 'FAIL' for r in results):
        sys.exit(1)
    elif any(r['status'] == 'DIFF' for r in results):
        sys.exit(2)
    sys.exit(0)


if __name__ == '__main__':
    main()
