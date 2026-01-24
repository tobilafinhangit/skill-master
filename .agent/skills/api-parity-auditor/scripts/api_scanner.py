import os
import re
import argparse
import json
import sys

class APIScanner:
    def __init__(self, source_path, target_path):
        self.source_path = source_path
        self.target_path = target_path
        self.source_endpoints = []
        self.target_endpoints = []
        self.source_frameworks = []
        self.target_frameworks = []

    def detect_frameworks(self, path):
        frameworks = []
        if os.path.exists(os.path.join(path, "supabase", "functions")):
            frameworks.append("Supabase")
        
        package_json = os.path.join(path, "package.json")
        if os.path.exists(package_json):
            with open(package_json, 'r') as f:
                content = f.read()
                if '"express"' in content:
                    frameworks.append("Express")
        
        # Check nested backend folder
        if not frameworks:
            backend_path = os.path.join(path, "backend")
            if os.path.exists(backend_path):
                return self.detect_frameworks(backend_path)

        return frameworks

    def scan_express(self, path):
        endpoints = []
        pattern = re.compile(r'(?:app|router|route)\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]', re.IGNORECASE)
        
        for root, _, files in os.walk(path):
            if "node_modules" in root: continue
            for file in files:
                if file.endswith((".js", ".ts")):
                    with open(os.path.join(root, file), 'r', errors='ignore') as f:
                        content = f.read()
                        matches = pattern.findall(content)
                        for method, route in matches:
                            endpoints.append({"method": method.upper(), "path": route, "origin": "Express"})
        return endpoints

    def scan_supabase(self, path):
        endpoints = []
        functions_path = os.path.join(path, "supabase", "functions")
        if os.path.exists(functions_path):
            for item in os.listdir(functions_path):
                if os.path.isdir(os.path.join(functions_path, item)) and not item.startswith("_"):
                    endpoints.append({"method": "POST/RPC", "path": f"/functions/v1/{item}", "origin": "Supabase"})
        return endpoints

    def run_scan(self):
        self.source_frameworks = self.detect_frameworks(self.source_path)
        self.target_frameworks = self.detect_frameworks(self.target_path)

        if "Express" in self.source_frameworks:
            self.source_endpoints.extend(self.scan_express(self.source_path))
        if "Supabase" in self.source_frameworks:
            self.source_endpoints.extend(self.scan_supabase(self.source_path))

        if "Express" in self.target_frameworks:
            self.target_endpoints.extend(self.scan_express(self.target_path))
        if "Supabase" in self.target_frameworks:
            self.target_endpoints.extend(self.scan_supabase(self.target_path))

        return self.compare()

    def compare(self):
        def normalize_name(p):
            name = p.strip("/").split("/")[-1]
            # Remove common prefixes/suffixes for matching
            name = re.sub(r'^fn_', '', name)
            name = re.sub(r'[-_]', '', name).lower()
            return name

        missing = []
        for s_ep in self.source_endpoints:
            s_norm = normalize_name(s_ep['path'])
            found = False
            for t_ep in self.target_endpoints:
                t_norm = normalize_name(t_ep['path'])
                if s_norm == t_norm:
                    found = True
                    break
            if not found:
                print(f"DEBUG: Missing {s_ep['path']} -> normalized: {s_norm}", file=sys.stderr)
                missing.append(s_ep)
            else:
                # print(f"DEBUG: Found {s_ep['path']} -> matched: {t_norm}", file=sys.stderr)
                pass

        return {
            "source_frameworks": self.source_frameworks,
            "target_frameworks": self.target_frameworks,
            "source_count": len(self.source_endpoints),
            "target_count": len(self.target_endpoints),
            "missing": missing,
            "all_source": self.source_endpoints,
            "all_target": self.target_endpoints
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()

    scanner = APIScanner(args.source, args.target)
    results = scanner.run_scan()
    print(json.dumps(results, indent=2))
