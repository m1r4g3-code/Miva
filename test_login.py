"""
MIVA LMS - LOGIN TEST SCRIPT
Use this to test if login works before running full automation
"""

import asyncio
from playwright.async_api import async_playwright

async def test_login():
    print("\n" + "=" * 70)
    print("🔍 MIVA LMS LOGIN TEST")
    print("=" * 70)
    print("\nThis script will:")
    print("1. Open browser")
    print("2. Navigate to Miva LMS")
    print("3. Wait for you to log in")
    print("4. Verify if login worked")
    print("5. Save cookies if successful")
    print("\n" + "=" * 70 + "\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--start-maximized', '--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        print("⏳ Opening Miva LMS...")
        await page.goto("https://lms.miva.university/my/courses.php")
        
        print("\n📋 INSTRUCTIONS:")
        print("1. Log in to your account in the browser")
        print("2. Wait until you see your COURSES DASHBOARD")
        print("3. Come back here and press ENTER")
        print("\nPress ENTER when you're logged in and on the courses page...")
        input()
        
        # Check what's on the page
        current_url = page.url
        print(f"\n🔍 Current URL: {current_url}")
        
        # Try to find courses
        course_count = await page.locator(".coursebox, .course-listitem, a[href*='course/view.php']").count()
        print(f"📚 Found {course_count} course elements")
        
        # Check for user menu
        user_menu = await page.locator(".usermenu, .user-picture, [data-region='user-menu']").count()
        print(f"👤 Found {user_menu} user menu elements")
        
        # Determine if logged in
        if course_count > 0 or user_menu > 0:
            print("\n✅ SUCCESS! You are logged in!")
            print("\nSaving cookies...")
            
            # Save cookies
            cookies = await context.cookies()
            import json
            with open("miva_session_cookies.json", "w") as f:
                json.dump(cookies, f, indent=2)
            
            print("✅ Cookies saved to: miva_session_cookies.json")
            print("\nYou can now run the main automation script:")
            print("   python miva_automation.py")
            print("\nIt will use these saved cookies!")
        else:
            print("\n❌ FAILED - Could not detect login")
            print("\nPossible issues:")
            print("1. You're not on the courses dashboard page")
            print("2. Page hasn't fully loaded yet")
            print("3. You're still on the login page")
            print("\nCurrent page title:", await page.title())
            print("\nTry again:")
            print("1. Make sure you're logged in")
            print("2. Navigate to the courses page")
            print("3. Re-run this test script")
        
        print("\n" + "=" * 70)
        print("Press ENTER to close browser...")
        input()
        
        await browser.close()

if __name__ == "__main__":
    print("\nStarting login test...")
    try:
        asyncio.run(test_login())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
