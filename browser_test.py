from browser_use.browser.session import BrowserSession
import asyncio

async def test():
    session = BrowserSession(headless=False)
    await session.start()
    page = await session.get_current_page()
    await page.goto("https://example.com")
    print("Title:", await page.title())
    await asyncio.sleep(3)
    await session.kill()

asyncio.run(test())
