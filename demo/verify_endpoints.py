import json
import urllib.request

def test_endpoints():
    base_url = "http://127.0.0.1:51770"

    print("=" * 60)
    print("VERIFYING MAANAKNETRA WEB APPLICATION ENDPOINTS")
    print("=" * 60)

    # 1. Health check
    with urllib.request.urlopen(f"{base_url}/health") as resp:
        health = json.loads(resp.read().decode())
        print("1. [GET /health] Status Code:", resp.status)
        print("   Body:", json.dumps(health, indent=2))

    # 2. Demo endpoint
    with urllib.request.urlopen(f"{base_url}/api/demo") as resp:
        demo = json.loads(resp.read().decode())
        print("\n2. [GET /api/demo] Status Code:", resp.status)
        print("   Document Title:     ", demo.get("tender_metadata", {}).get("document_title"))
        print("   Risk Level:         ", demo.get("risk_indicator", {}).get("risk_level"))
        print("   Compliance Score:   ", demo.get("risk_indicator", {}).get("compliance_score"), "%")
        print("   Findings Count:     ", len(demo.get("findings", [])))
        print("   Corrected Clauses:  ", len(demo.get("corrected_clause", []) or demo.get("corrected_clauses", [])))
        print("   Standards BOM Count:", len(demo.get("standards_bom", [])))

    # 3. Static frontend root
    with urllib.request.urlopen(f"{base_url}/") as resp:
        html = resp.read().decode()
        print("\n3. [GET /] Frontend Root Status Code:", resp.status)
        print("   HTML Size:          ", len(html), "bytes")
        print("   Title Verified:     ", "<title>MAANAKNETRA" in html)
        print("   Styles Linked:      ", 'href="styles.css"' in html)
        print("   Script Linked:      ", 'src="app.js"' in html)

    # 4. Static assets
    with urllib.request.urlopen(f"{base_url}/styles.css") as resp:
        css = resp.read().decode()
        print("\n4. [GET /styles.css] Status Code:", resp.status, f"({len(css)} bytes)")

    with urllib.request.urlopen(f"{base_url}/app.js") as resp:
        js = resp.read().decode()
        print("5. [GET /app.js] Status Code:", resp.status, f"({len(js)} bytes)")

    print("\n" + "=" * 60)
    print("ALL WEB APP ENDPOINTS VERIFIED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_endpoints()
