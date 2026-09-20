with open("README.md", "r", encoding="utf-8") as f:
    content = f.read()

if "actions/workflows/tests.yml" not in content:
    # Add badge after title
    badge = "\n[![Tests](https://github.com/Pappu246/nova-assistant/actions/workflows/tests.yml/badge.svg)](https://github.com/Pappu246/nova-assistant/actions/workflows/tests.yml)\n"
    content = content.replace(
        "# NOVA - Personal AI Assistant\n",
        "# NOVA - Personal AI Assistant\n" + badge,
        1
    )
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)
    print("CI badge added to README")
else:
    print("Badge already present")
