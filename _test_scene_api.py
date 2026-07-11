"""Comprehensive smoke test for scene orchestration API endpoints."""
import requests
import json
import sys
import io

BASE = "http://127.0.0.1:8000"
s = requests.Session()

# ── Login ──
r = s.post(BASE + "/api/v1/auth/login/", json={"username": "admin", "password": "admin"}, headers={"Referer": BASE})
assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:200]}"
csrf = s.cookies.get("csrftoken", "")
H = {"X-CSRFToken": csrf, "Referer": BASE}
print("[OK] Login")

# ── 1. List scenes ──
r = s.get(BASE + "/api/v1/test-scenes/", headers=H)
assert r.status_code == 200, f"List scenes failed: {r.status_code} {r.text[:200]}"
data = r.json()
scenes = data if isinstance(data, list) else data.get("results", [])
print(f"[OK] List scenes: {len(scenes)} scene(s)")

if not scenes:
    print("No scenes to test, exiting.")
    sys.exit(0)

sid = scenes[0]["id"]
project_id = scenes[0].get("project")  # might be int or nested
if isinstance(project_id, dict):
    project_id = project_id.get("id")
print(f"     Testing scene: id={sid}, name={scenes[0]['name']}, project_id={project_id}")

# ── 2. Scene detail ──
r = s.get(BASE + f"/api/v1/test-scenes/{sid}/", headers=H)
assert r.status_code == 200, f"Scene detail failed: {r.status_code}"
detail = r.json()
print(f"[OK] Scene detail: name={detail['name']}")

# ── 3. List nodes (full) ──
r = s.get(BASE + f"/api/v1/test-scene-nodes/?scene_id={sid}", headers=H)
assert r.status_code == 200, f"List nodes failed: {r.status_code} {r.text[:200]}"
nodes = r.json() if isinstance(r.json(), list) else r.json().get("results", [])
print(f"[OK] List nodes: {len(nodes)} node(s)")
for n in nodes[:5]:
    m = n.get("method", "MISSING")
    am = n.get("api_asset_method", "MISSING")
    print(f"     {n['name']} | method={m} | api_asset_method={am}")

# ── 4. Node detail ──
if nodes:
    nid = nodes[0]["id"]
    r = s.get(BASE + f"/api/v1/test-scene-nodes/{nid}/", headers=H)
    assert r.status_code == 200, f"Node detail failed: {r.status_code}"
    nd = r.json()
    print(f"[OK] Node detail: method={nd.get('method','MISSING')} | api_asset_method={nd.get('api_asset_method','MISSING')}")

# ── 5. Optimized fields list ──
r = s.get(BASE + f"/api/v1/test-scene-nodes/?scene_id={sid}&fields=id,name,method,is_enabled,sort", headers=H)
assert r.status_code == 200, f"Optimized list failed: {r.status_code} {r.text[:200]}"
opt = r.json() if isinstance(r.json(), list) else r.json().get("results", [])
print(f"[OK] Optimized list: {len(opt)} node(s)")
for n in opt[:3]:
    print(f"     {json.dumps(n, ensure_ascii=False)}")

# ── 6. Update node method ──
if nodes:
    nid = nodes[0]["id"]
    old_method = nodes[0].get("method", "")
    r = s.patch(BASE + f"/api/v1/test-scene-nodes/{nid}/", json={"method": "POST"}, headers=H)
    assert r.status_code == 200, f"Update method failed: {r.status_code} {r.text[:200]}"
    ud = r.json()
    assert ud.get("method") == "POST", f"Method not updated: {ud.get('method')}"
    print(f"[OK] Update method -> POST")
    # Restore
    r = s.patch(BASE + f"/api/v1/test-scene-nodes/{nid}/", json={"method": old_method}, headers=H)
    print(f"     Restored to: {r.json().get('method')}")

# ── 7. Copy node ──
if nodes:
    nid = nodes[0]["id"]
    r = s.post(BASE + f"/api/v1/test-scene-nodes/{nid}/copy/", headers=H)
    assert r.status_code == 201, f"Copy node failed: {r.status_code} {r.text[:200]}"
    cn = r.json()
    assert cn.get("method"), f"Copied node has no method: {cn.get('method')}"
    print(f"[OK] Copy node: id={cn['id']}, name={cn['name']}, method={cn.get('method')}")
    # Cleanup
    s.delete(BASE + f"/api/v1/test-scene-nodes/{cn['id']}/", headers=H)

# ── 8. Copy scene ──
r = s.post(BASE + f"/api/v1/test-scenes/{sid}/copy/", json={"name": "__test_copy__"}, headers=H)
assert r.status_code == 201, f"Copy scene failed: {r.status_code} {r.text[:200]}"
cs = r.json()
csid = cs["id"]
print(f"[OK] Copy scene: id={csid}, name={cs['name']}")
# Check copied nodes have method
r2 = s.get(BASE + f"/api/v1/test-scene-nodes/?scene_id={csid}", headers=H)
cnodes = r2.json() if isinstance(r2.json(), list) else r2.json().get("results", [])
for cn in cnodes[:3]:
    print(f"     Copied node: {cn['name']} | method={cn.get('method', 'MISSING')}")
# Cleanup
s.delete(BASE + f"/api/v1/test-scenes/{csid}/", headers=H)

# ── 9. Export scenes (fix: content field) ──
export_payload = {"scene_ids": [sid]}
if project_id:
    export_payload["project_id"] = project_id
r = s.post(BASE + "/api/v1/test-scenes/export-scenes/", json=export_payload, headers=H)
assert r.status_code == 200, f"Export failed: {r.status_code} {r.text[:200]}"
export_resp = r.json()
print(f"     Export response keys: {list(export_resp.keys())}")

# The actual export data is inside 'content'
if "content" in export_resp:
    export_data = export_resp["content"]
else:
    export_data = export_resp
exported_scenes = export_data.get("scenes", [])
total_nodes = sum(len(sc.get("nodes", [])) for sc in exported_scenes)
print(f"[OK] Export: {len(exported_scenes)} scene(s), {total_nodes} node(s)")

# Verify method field in exported nodes
method_ok = 0
method_missing = 0
for sc in exported_scenes:
    for n in sc.get("nodes", []):
        m = n.get("method", "")
        if m:
            method_ok += 1
        else:
            method_missing += 1
        if method_ok <= 3:
            print(f"     Exported node: {n['name']} | method={m or 'EMPTY'}")
print(f"     Method stats: {method_ok} with method, {method_missing} without")
if method_missing > 0:
    print(f"     [WARN] {method_missing} exported node(s) have no method")

# ── 10. Import preview (upload exported JSON) ──
export_json_bytes = json.dumps(export_data, ensure_ascii=False).encode("utf-8")
files_payload = {
    "file": ("export_test.json", io.BytesIO(export_json_bytes), "application/json"),
}
preview_payload = {}
if project_id:
    preview_payload["project_id"] = str(project_id)

r = s.post(
    BASE + "/api/v1/test-scenes/import-scenes/preview",
    files=files_payload,
    data=preview_payload,
    headers=H,
)
if r.status_code == 200:
    preview = r.json()
    summary = preview.get("summary", {})
    conflicts = preview.get("conflicts", {})
    print(f"[OK] Import preview: {summary}")
    has_conflicts = any(len(v) > 0 for v in conflicts.values())
    if has_conflicts:
        print(f"     Conflicts detected: { {k: len(v) for k, v in conflicts.items() if v} }")
    else:
        print(f"     No conflicts")
elif r.status_code == 400:
    print(f"[WARN] Import preview 400: {r.text[:300]}")
else:
    print(f"[FAIL] Import preview: {r.status_code} {r.text[:300]}")

# ── 11. Import confirm (with skip strategy to avoid duplicates) ──
import_payload = {
    "project_id": project_id,
    "data": export_data,
    "default_conflict_strategy": "skip",
}
r = s.post(BASE + "/api/v1/test-scenes/import-scenes/confirm", json=import_payload, headers=H)
if r.status_code == 200:
    stats = r.json()
    print(f"[OK] Import confirm: {json.dumps(stats, ensure_ascii=False)}")
    # Check imported nodes have method
    # Find newly created scenes
    r2 = s.get(BASE + "/api/v1/test-scenes/", headers=H)
    all_scenes = r2.json() if isinstance(r2.json(), list) else r2.json().get("results", [])
    print(f"     Total scenes after import: {len(all_scenes)}")
else:
    print(f"[WARN] Import confirm: {r.status_code} {r.text[:300]}")

# ── 12. API Diff ──
if nodes:
    nid = nodes[0]["id"]
    r = s.get(BASE + f"/api/v1/test-scene-nodes/{nid}/api-diff/", headers=H)
    if r.status_code == 200:
        diff = r.json()
        basic = diff.get("diffs", {}).get("basic", {})
        print(f"[OK] API Diff: {json.dumps(basic, ensure_ascii=False)[:200]}")
    elif r.status_code == 400:
        print(f"[OK] API Diff: no asset linked (expected for some nodes)")
    else:
        print(f"[WARN] API Diff: status={r.status_code}")

# ── 13. Sync basic ──
if nodes:
    nid = nodes[0]["id"]
    r = s.post(BASE + f"/api/v1/test-scene-nodes/{nid}/sync-basic/", headers=H)
    if r.status_code in (200, 400):
        print(f"[OK] Sync basic: {r.json().get('detail', r.status_code)}")
    else:
        print(f"[WARN] Sync basic: status={r.status_code}")

# ── 14. Scene execution (need environment) ──
# First, list environments to find one
r = s.get(BASE + "/api/v1/environments/", headers=H)
envs = []
if r.status_code == 200:
    envs = r.json() if isinstance(r.json(), list) else r.json().get("results", [])
    print(f"[INFO] Found {len(envs)} environment(s)")

if envs and project_id:
    # Find environment matching the project
    env_id = None
    for e in envs:
        ep = e.get("project")
        if isinstance(ep, dict):
            ep = ep.get("id")
        if ep == project_id or ep == int(project_id):
            env_id = e["id"]
            break
    if not env_id and envs:
        env_id = envs[0]["id"]
    
    if env_id:
        print(f"[INFO] Using environment id={env_id} for execution test")
        # Try single node execution first (if we have nodes)
        if nodes:
            # Find an enabled node
            enabled_nodes = [n for n in nodes if n.get("is_enabled", True)]
            if enabled_nodes:
                test_node = enabled_nodes[0]
                exec_payload = {
                    "run_mode": "single",
                    "node_id": test_node["id"],
                    "environment_id": env_id,
                }
                r = s.post(BASE + f"/api/v1/test-scenes/{sid}/execute/", json=exec_payload, headers=H, timeout=30)
                if r.status_code == 200:
                    exec_result = r.json()
                    exec_status = exec_result.get("status", "unknown")
                    print(f"[OK] Scene execute (single): status={exec_status}")
                    # Check node results
                    node_results = exec_result.get("node_results", [])
                    for nr in node_results[:3]:
                        nr_status = nr.get("status", "?")
                        nr_name = nr.get("node_name", nr.get("name", "?"))
                        print(f"     Node result: {nr_name} -> {nr_status}")
                elif r.status_code == 500:
                    err = r.json()
                    print(f"[WARN] Scene execute (single) 500: {err.get('error_message', err.get('detail', ''))[:200]}")
                else:
                    print(f"[WARN] Scene execute: {r.status_code} {r.text[:200]}")
        
        # Try full scene execution
        exec_payload_all = {
            "run_mode": "all",
            "environment_id": env_id,
        }
        r = s.post(BASE + f"/api/v1/test-scenes/{sid}/execute/", json=exec_payload_all, headers=H, timeout=60)
        if r.status_code == 200:
            exec_result = r.json()
            exec_status = exec_result.get("status", "unknown")
            print(f"[OK] Scene execute (all): status={exec_status}")
            node_results = exec_result.get("node_results", [])
            print(f"     Total node results: {len(node_results)}")
            for nr in node_results[:5]:
                nr_status = nr.get("status", "?")
                nr_name = nr.get("node_name", nr.get("name", "?"))
                print(f"     Node result: {nr_name} -> {nr_status}")
        elif r.status_code == 500:
            err = r.json()
            print(f"[WARN] Scene execute (all) 500: {err.get('error_message', err.get('detail', ''))[:200]}")
        else:
            print(f"[WARN] Scene execute (all): {r.status_code} {r.text[:200]}")
    else:
        print("[SKIP] No matching environment for execution test")
else:
    print("[SKIP] No environments available for execution test")

# ── 15. List executions ──
r = s.get(BASE + f"/api/v1/test-scenes/{sid}/executions/", headers=H)
if r.status_code == 200:
    execs = r.json() if isinstance(r.json(), list) else r.json().get("results", [])
    print(f"[OK] List executions: {len(execs)} execution(s)")
    for ex in execs[:3]:
        print(f"     id={ex['id']} status={ex.get('status')} started={ex.get('started_at', '?')[:19]}")
else:
    print(f"[WARN] List executions: {r.status_code}")

# ── 16. Replay import preview ──
r = s.post(
    BASE + "/api/v1/test-scenes/replay-import/preview",
    files=files_payload,
    data=preview_payload,
    headers=H,
)
if r.status_code == 200:
    replay_preview = r.json()
    print(f"[OK] Replay import preview: {json.dumps(replay_preview, ensure_ascii=False)[:300]}")
elif r.status_code in (400, 404):
    print(f"[WARN] Replay import preview: {r.status_code} {r.text[:200]}")
else:
    print(f"[INFO] Replay import preview: {r.status_code}")

print("\n=== All scene orchestration API tests completed! ===")
