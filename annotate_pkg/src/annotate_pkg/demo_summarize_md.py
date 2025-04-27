import os
from annotate_pkg.client import LLMClient

MD_DIR = "/home/dev/ThinkMark/output-md/raw_html"

def main():
    client = LLMClient()
    for fname in os.listdir(MD_DIR):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(MD_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"\n=== {fname} ===")
        try:
            resp = client.summarize_markdown(content)
            summary = resp.choices[0].message.content if hasattr(resp, "choices") else resp
            print(summary)
        except Exception as e:
            print(f"Error summarizing {fname}: {e}")

if __name__ == "__main__":
    main()
