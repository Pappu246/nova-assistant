with open("browser_agent.py", "r", encoding="utf-8") as f:
    src = f.read()

old = """    browser = Browser(headless=False)
    agent = Agent(
        task=task_english,
        llm=llm,
        fallback_llm=fallback,
        browser=browser,
        use_vision=True,
    )
    return await agent.run(max_steps=25)"""

new = """    browser = Browser(
        headless=False,
        keep_alive=True,          # Task ke baad browser khula rahe
        user_data_dir=None,
    )
    agent = Agent(
        task=task_english,
        llm=llm,
        fallback_llm=fallback,
        browser=browser,
        use_vision=True,
    )
    result = await agent.run(max_steps=25)
    # NOTE: browser.close() intentionally NOT called
    # User "browser band karo" bole tabhi band karenge
    return result"""

if old in src:
    src = src.replace(old, new)
    with open("browser_agent.py", "w", encoding="utf-8") as f:
        f.write(src)
    print("browser_agent.py updated - keep_alive=True")
else:
    print("Old block not found, check manually")
