with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add memory tools to prompt
if "remember - " not in src:
    src = src.replace(
        '20. web_search - {"query": "..."}',
        '''20. web_search - {"query": "..."}
21. remember - {"key": "user_name", "value": "Pappu"}  (kuch yaad rakhna)
22. recall - {"key": "user_name"}  (kuch yaad karna, key khaali chhodo to sab dikhao)
23. forget - {"key": "user_name"}  (kuch bhoolna)
24. note - {"content": "kal 5 baje meeting"}  (note banana)
25. list_notes - {}  (saare notes dikhao)'''
    )

    src = src.replace(
        '- X type karo / likho -> type_text',
        '''- X type karo / likho -> type_text
- "yaad rakho X Y hai" / "remember X" -> remember key=X value=Y
- "mera naam X hai" -> remember key=user_name value=X
- "mera X kya hai" / "X kya tha" -> recall key=X
- "kya yaad hai" / "sab batao" -> recall key=""
- "X bhool jao" -> forget key=X
- "note karo X" / "yaad dilana X" -> note content=X
- "mere notes" / "notes dikhao" -> list_notes'''
    )

with open("brain.py", "w", encoding="utf-8") as f:
    f.write(src)

print("brain.py updated")