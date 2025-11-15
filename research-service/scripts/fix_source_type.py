import re
import sys

files = [
    "tests/unit/utils/test_authority_scorer.py",
    "tests/integration/test_authority_scoring_integration.py",
    "tests/e2e/test_search_with_authority.py",
    "tests/conftest.py",
]

for filepath in files:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Add source_type="web" before closing paren if relevance= exists and source_type doesn't
        lines = content.split("\n")
        modified_lines = []

        for i, line in enumerate(lines):
            if "SearchSource(" in line:
                # Start collecting the full SearchSource call
                call_lines = [line]
                paren_count = line.count("(") - line.count(")")
                j = i + 1

                while paren_count > 0 and j < len(lines):
                    call_lines.append(lines[j])
                    paren_count += lines[j].count("(") - lines[j].count(")")
                    j += 1

                full_call = "\n".join(call_lines)

                # Check if source_type already exists
                if "source_type" not in full_call and "relevance=" in full_call:
                    # Find last occurrence of relevance=X.X
                    match = re.search(r"(relevance=[\d.]+)(\s*[,)])", full_call)
                    if match:
                        # Add source_type after relevance
                        full_call = full_call.replace(
                            match.group(0), match.group(1) + ', source_type="web"' + match.group(2)
                        )

                # Replace in modified_lines
                modified_lines.extend(full_call.split("\n"))

                # Skip the lines we already processed
                for _ in range(len(call_lines) - 1):
                    i += 1
            else:
                if i >= len(modified_lines):
                    modified_lines.append(line)

        # Simpler approach: regex replacement
        content = re.sub(
            r"(relevance\s*=\s*[\d.]+)(\s*)(\))",
            lambda m: f'{m.group(1)}, source_type="web"{m.group(2)}{m.group(3)}'
            if "source_type"
            not in content[max(0, content.find(m.group(0)) - 200) : content.find(m.group(0)) + 200]
            else m.group(0),
            content,
        )

        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ Fixed {filepath}")
        else:
            print(f"- No changes needed for {filepath}")

    except Exception as e:
        print(f"✗ Error processing {filepath}: {e}")
        sys.exit(1)

print("\nDone!")
