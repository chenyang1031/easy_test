"""Quick smoke test for scene orchestration API endpoints."""
import requests
import json
import sys

BASE = "http://127.0.0.1:8000"
s = requests.Session()

# Login
r = s.post(BASE + "/api/v1/auth/login/", json={"username": "admin", "password": "admin"}, headers={"Referer": BASE})
assert r.status_code == 200, f"Login failed: {r.status_code}"
csrf = s.cookies.get("csrftoken", "")
H = {"X-CSRFToken": csrf, "Referer": BASE}
print("[OK] Login")

# 1. List scenes
r = s.get(BASE + "/api/v1/test-scenes/", headers=H)
assert r.status_code == 200, f"List scenes failed: {r.status_code} {r.text[:200]}"
data = r.json()
scenes = data if isinstance(data, list) else data.get("results", [])
print(f"[OK] List scenes: {len(scenes)} scene(s)")

if not scenes:
    print("No scenes to test, exiting.")
    sys.exit(0)

sid = scenes[0]["id"]
print(f"     Testing scene: id={sid}, name={scenes[0]['name']}")

# 2. Scene detail
r = s.get(BASE + f"/api/v1/test-scenes/{sid}/", headers=H)
assert r.status_code == 200, f"Scene detail failed: {r.status_code}"
detail = r.json()
print(f"[OK] Scene detail: name={detail['name']}")

# 3. List nodes (full)
r = s.get(BASE + f"/api/v1/test-scene-nodes/?scene_id={sid}", headers=H)
assert r.status_code == 200, f"List nodes failed: {r.status_code} {r.text[:200]}"
nodes = r.json() if isinstance(r.json(), list) else r.json().get("results", [])
print(f"[OK] List nodes: {len(nodes)} node(s)")
for n in nodes[:5]:
    m = n.get("method", "MISSING")
    am = n.get("api_asset_method", "MISSING")
    print(f"     {n['name']} | method={m} | api_asset_method={am}")

# 4. Node detail
if nodes:
    nid = nodes[0]["id"]
    r = s.get(BASE + f"/api/v1/test-scene-nodes/{nid}/", headers=H)
    assert r.status_code == 200, f"Node detail failed: {r.status_code}"
    nd = r.json()
    print(f"[OK] Node detail: method={nd.get('method','MISSING')} | api_asset_method={nd.get('api_asset_method','MISSING')}")

# 5. Optimized fields list
r = s.get(BASE + f"/api/v1/test-scene-nodes/?scene_id={sid}&fields=id,name,method,is_enabled,sort", headers=H)
assert r.status_code == 200, f"Optimized list failed: {r.status_code} {r.text[:200]}"
opt = r.json() if isinstance(r.json(), list) else r.json().get("results", [])
print(f"[OK] Optimized list: {len(opt)} node(s)")
for n in opt[:3]:
    print(f"     {json.dumps(n, ensure_ascii=False)}")

# 6. Update node method
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

# 7. Copy node
if nodes:
    nid = nodes[0]["id"]
    r = s.post(BASE + f"/api/v1/test-scene-nodes/{nid}/copy/", headers=H)
    assert r.status_code == 201, f"Copy node failed: {r.status_code} {r.text[:200]}"
    cn = r.json()
    assert cn.get("method"), f"Copied node has no method: {cn.get('method')}"
    print(f"[OK] Copy node: id={cn['id']}, name={cn['name']}, method={cn.get('method')}")
    # Cleanup
    s.delete(BASE + f"/api/v1/test-scene-nodes/{cn['id']}/", headers=H)

# 8. Copy scene
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

# 9. Export scenes
r = s.post(BASE + "/api/v1/test-scenes/export-scenes/", json={"scene_ids": [sid]}, headers=H)
assert r.status_code == 200, f"Export failed: {r.status_code} {r.text[:200]}"
export_data = r.json()
exported_scenes = export_data.get("scenes", [])
total_nodes = sum(len(sc.get("nodes", [])) for sc in exported_scenes)
print(f"[OK] Export: {len(exported_scenes)} scene(s), {total_nodes} node(s)")
for sc in exported_scenes:
    for n in sc.get("nodes", [])[:2]:
        print(f"     Exported node: {n['name']} | method={n.get('method', 'MISSING')}")

# 10. API Diff
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

# 11. Sync basic
if nodes:
    nid = nodes[0]["id"]
    r = s.post(BASE + f"/api/v1/test-scene-nodes/{nid}/sync-basic/", headers=H)
    if r.status_code in (200, 400):
        print(f"[OK] Sync basic: {r.json().get('detail', r.status_code)}")
    else:
        print(f"[WARN] Sync basic: status={r.status_code}")

print("\n=== All scene orchestration API tests PASSED! ===")
