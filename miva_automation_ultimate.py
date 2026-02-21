"""
MIVA LMS AUTOMATION - ULTIMATE VERSION
Features:
- Reconnaissance scan
- Smart resume (prioritizes incomplete courses)
- Parallel processing (4 tabs)
- Optimized balanced-fast speed
- Better error handling with retries
- Detailed progress tracking
"""

import asyncio
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "base_url": "https://lms.miva.university",
    "courses_url": "https://lms.miva.university/my/courses.php",
    "cookies_file": "miva_session_cookies.json",
    "progress_file": "miva_progress.json",
    "screenshots_dir": "miva_screenshots",
    
    # OPTIMIZED BALANCED-FAST TIMING
    "page_load_wait": (0.8, 1.5),
    "content_view_time": (1.5, 2.5),
    "between_activities": (0.3, 0.7),
    "between_courses": (2, 4),
    "scroll_pause": (0.1, 0.2),
    
    # PARALLEL PROCESSING
    "parallel_tabs": 4,  # Process 4 activities at once
    "max_retries": 3,    # Retry failed activities 3 times
    
    # Behavior
    "skip_quizzes": True,
    "skip_assignments": True,
    "auto_resume": True,
    "run_reconnaissance": True,
    "headless": False,
    
    # Activity patterns
    "skip_patterns": ["/mod/quiz/", "/mod/assign/"],
    "complete_patterns": ["/mod/page/", "/mod/url/", "/mod/forum/", "/mod/book/"],
}

# ============================================================================
# PROGRESS MANAGER
# ============================================================================

class ProgressManager:
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.data = self.load()
    
    def load(self) -> Dict:
        """Load existing progress"""
        if self.filepath.exists():
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "last_run": None,
            "courses": {},
            "global_stats": {
                "total_completed": 0,
                "total_skipped": 0,
                "total_failed": 0
            }
        }
    
    def save(self):
        """Save current progress"""
        self.data["last_run"] = datetime.now().isoformat()
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def get_course_progress(self, course_id: str) -> Dict:
        """Get progress for a specific course"""
        if course_id not in self.data["courses"]:
            self.data["courses"][course_id] = {
                "name": "",
                "status": "not_started",
                "completed_activities": [],
                "failed_activities": [],
                "total_activities": 0,
                "last_activity_index": 0
            }
        return self.data["courses"][course_id]
    
    def mark_activity_completed(self, course_id: str, activity_url: str):
        """Mark an activity as completed"""
        course = self.get_course_progress(course_id)
        if activity_url not in course["completed_activities"]:
            course["completed_activities"].append(activity_url)
        self.save()
    
    def mark_activity_failed(self, course_id: str, activity_url: str, error: str):
        """Mark an activity as failed"""
        course = self.get_course_progress(course_id)
        failure = {"url": activity_url, "error": error, "timestamp": datetime.now().isoformat()}
        course["failed_activities"].append(failure)
        self.save()
    
    def is_activity_completed(self, course_id: str, activity_url: str) -> bool:
        """Check if activity is already completed"""
        course = self.get_course_progress(course_id)
        return activity_url in course["completed_activities"]
    
    def get_course_completion_percent(self, course_id: str) -> float:
        """Get completion percentage for a course"""
        course = self.get_course_progress(course_id)
        if course["total_activities"] == 0:
            return 0
        return (len(course["completed_activities"]) / course["total_activities"]) * 100
    
    def prioritize_courses(self, courses: List[Dict]) -> List[Dict]:
        """Prioritize courses: in_progress > not_started > completed"""
        prioritized = []
        
        for course in courses:
            course_id = course.get("id", "")
            completion = self.get_course_completion_percent(course_id)
            
            if completion >= 100:
                course["_priority"] = 3  # Completed - lowest priority
                course["_completion"] = completion
            elif completion > 0:
                course["_priority"] = 1  # In progress - highest priority
                course["_completion"] = completion
            else:
                course["_priority"] = 2  # Not started - medium priority
                course["_completion"] = 0
        
        # Sort by priority (1 = highest), then by completion descending
        prioritized = sorted(courses, key=lambda c: (c["_priority"], -c["_completion"]))
        
        return prioritized

# ============================================================================
# STATISTICS TRACKER
# ============================================================================

class Statistics:
    def __init__(self):
        self.start_time = datetime.now()
        self.courses_processed = 0
        self.activities_completed = 0
        self.activities_skipped = 0
        self.activities_failed = 0
        self.quizzes_found = []
        self.assignments_found = []
        self.errors = []
        self.completed_activities = []
        
    def log_completed(self, course_name: str, activity_name: str, activity_type: str):
        self.activities_completed += 1
        self.completed_activities.append({
            "course": course_name,
            "activity": activity_name,
            "type": activity_type,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_skipped(self, course_name: str, activity_name: str, activity_type: str):
        self.activities_skipped += 1
        if "quiz" in activity_type.lower():
            self.quizzes_found.append({"course": course_name, "activity": activity_name})
        elif "assign" in activity_type.lower():
            self.assignments_found.append({"course": course_name, "activity": activity_name})
    
    def log_error(self, message: str):
        self.errors.append({"message": message, "timestamp": datetime.now().isoformat()})
        self.activities_failed += 1
    
    def get_duration(self) -> str:
        duration = datetime.now() - self.start_time
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        seconds = duration.seconds % 60
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        return f"{minutes}m {seconds}s"

stats = Statistics()
progress = ProgressManager(CONFIG["progress_file"])

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def log(message: str, level: str = "INFO"):
    """Enhanced logging"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    emoji = {
        "INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌",
        "SKIP": "⏭️", "PROGRESS": "⏳", "QUIZ": "📝", "ASSIGNMENT": "📋",
        "COURSE": "📚", "RECON": "🔍", "RESUME": "🔄", "PARALLEL": "⚡"
    }
    print(f"[{timestamp}] {emoji.get(level, '📌')} {message}")

async def random_delay(min_sec: float, max_sec: float):
    """Async random delay"""
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def human_scroll(page: Page):
    """Fast but natural scrolling"""
    try:
        page_height = await page.evaluate("document.documentElement.scrollHeight")
        viewport_height = await page.evaluate("window.innerHeight")
        
        # Quick scroll to bottom
        steps = 3
        for i in range(steps):
            position = (page_height / steps) * (i + 1)
            await page.evaluate(f"window.scrollTo({{top: {position}, behavior: 'smooth'}})")
            await asyncio.sleep(random.uniform(*CONFIG["scroll_pause"]))
        
    except Exception as e:
        pass

async def take_screenshot(page: Page, name: str):
    """Take screenshot for debugging"""
    try:
        screenshots_dir = Path(CONFIG["screenshots_dir"])
        screenshots_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = screenshots_dir / f"{timestamp}_{name}.png"
        await page.screenshot(path=str(filename))
        return str(filename)
    except:
        return None

# ============================================================================
# AUTHENTICATION MANAGER
# ============================================================================

class AuthManager:
    def __init__(self, context: BrowserContext):
        self.context = context
        self.cookies_file = Path(CONFIG["cookies_file"])
    
    async def load_cookies(self) -> bool:
        try:
            if self.cookies_file.exists():
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                await self.context.add_cookies(cookies)
                log("Loaded saved session cookies", "SUCCESS")
                return True
        except Exception as e:
            log(f"Could not load cookies: {e}", "WARNING")
        return False
    
    async def save_cookies(self):
        try:
            cookies = await self.context.cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            log("Saved session cookies", "SUCCESS")
        except Exception as e:
            log(f"Could not save cookies: {e}", "WARNING")
    
    async def check_logged_in(self, page: Page) -> bool:
        try:
            current_url = page.url
            
            if "cas/login" in current_url or "sis.miva.university" in current_url:
                return False
            
            if "lms.miva.university" in current_url:
                await asyncio.sleep(1)
                course_elements = await page.locator(".coursebox, .course-listitem, a[href*='course/view.php']").count()
                user_menu = await page.locator(".usermenu, .user-picture, [data-region='user-menu']").count()
                
                if course_elements > 0 or user_menu > 0:
                    return True
            
            return False
        except:
            return False

# ============================================================================
# RECONNAISSANCE - Scan all courses first
# ============================================================================

async def run_reconnaissance(page: Page, courses: List[Dict]) -> Dict:
    """Scan all courses to understand structure and count activities"""
    log("\n" + "=" * 70, "RECON")
    log("🔍 RECONNAISSANCE PHASE - Scanning all courses...", "RECON")
    log("=" * 70 + "\n", "RECON")
    
    recon_data = {
        "total_courses": len(courses),
        "total_activities": 0,
        "total_to_process": 0,
        "total_to_skip": 0,
        "courses_detail": [],
        "estimated_time_minutes": 0
    }
    
    for i, course in enumerate(courses, 1):
        log(f"Scanning {i}/{len(courses)}: {course['name'][:50]}...", "PROGRESS")
        
        try:
            # Navigate to course
            await page.goto(course["url"], wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(1.5)
            
            # Expand sections
            try:
                buttons = await page.locator('.card-header a[data-toggle="collapse"]').all()
                for btn in buttons[:10]:  # Limit to avoid timeout
                    try:
                        await btn.click(timeout=500)
                    except:
                        pass
                await asyncio.sleep(0.5)
            except:
                pass
            
            # Count activities
            activity_links = await page.locator('a[href*="/mod/"]').all()
            
            activities = []
            seen = set()
            
            for link in activity_links:
                try:
                    href = await link.get_attribute("href")
                    if href and href not in seen and "/mod/" in href:
                        seen.add(href)
                        
                        activity_type = "unknown"
                        for pattern in ["/mod/page/", "/mod/url/", "/mod/quiz/", "/mod/assign/", "/mod/forum/"]:
                            if pattern in href:
                                activity_type = pattern.split("/")[2]
                                break
                        
                        should_skip = any(p in href for p in CONFIG["skip_patterns"])
                        activities.append({"type": activity_type, "skip": should_skip})
                except:
                    continue
            
            to_process = sum(1 for a in activities if not a["skip"])
            to_skip = sum(1 for a in activities if a["skip"])
            
            # Check existing progress
            course_progress = progress.get_course_progress(course["id"])
            already_done = len(course_progress["completed_activities"])
            remaining = max(0, to_process - already_done)
            
            course_detail = {
                "name": course["name"],
                "total_activities": len(activities),
                "to_process": to_process,
                "to_skip": to_skip,
                "already_done": already_done,
                "remaining": remaining,
                "completion_pct": (already_done / to_process * 100) if to_process > 0 else 0
            }
            
            recon_data["courses_detail"].append(course_detail)
            recon_data["total_activities"] += len(activities)
            recon_data["total_to_process"] += to_process
            recon_data["total_to_skip"] += to_skip
            
            log(f"  ✅ {to_process} to process | ⏭️  {to_skip} to skip | 🔄 {already_done} done", "INFO")
            
        except Exception as e:
            log(f"  Error scanning: {e}", "ERROR")
    
    # Calculate estimated time with parallel processing
    avg_time_per_activity = 3  # seconds (with balanced-fast mode)
    total_time_serial = recon_data["total_to_process"] * avg_time_per_activity
    total_time_parallel = total_time_serial / CONFIG["parallel_tabs"]
    recon_data["estimated_time_minutes"] = int(total_time_parallel / 60)
    
    # Display report
    log("\n" + "=" * 70, "SUCCESS")
    log("📊 RECONNAISSANCE REPORT", "SUCCESS")
    log("=" * 70, "SUCCESS")
    log(f"", "INFO")
    log(f"📚 Total Courses: {recon_data['total_courses']}", "INFO")
    log(f"📝 Total Activities: {recon_data['total_activities']}", "INFO")
    log(f"✅ Will Process: {recon_data['total_to_process']}", "SUCCESS")
    log(f"⏭️  Will Skip: {recon_data['total_to_skip']}", "SKIP")
    log(f"", "INFO")
    log(f"⏱️  Estimated Time: ~{recon_data['estimated_time_minutes']} minutes", "INFO")
    log(f"   (Using 4 parallel tabs + balanced-fast speed)", "INFO")
    log(f"", "INFO")
    
    # Show course breakdown
    log("📋 Course Breakdown:", "INFO")
    for detail in recon_data["courses_detail"]:
        status_icon = "✅" if detail["completion_pct"] >= 100 else "🔄" if detail["completion_pct"] > 0 else "⏳"
        log(f"  {status_icon} {detail['name'][:45]}", "INFO")
        log(f"     {detail['remaining']} remaining | {int(detail['completion_pct'])}% done", "INFO")
    
    log("=" * 70 + "\n", "SUCCESS")
    
    return recon_data

# ============================================================================
# COURSE & ACTIVITY DISCOVERY
# ============================================================================

async def discover_courses(page: Page) -> List[Dict]:
    """Find all courses"""
    log("Discovering courses...", "PROGRESS")
    
    try:
        await page.goto(CONFIG["courses_url"], wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)
        
        course_elements = await page.locator('a[href*="course/view.php"]').all()
        
        courses = []
        seen_urls = set()
        
        for element in course_elements:
            try:
                href = await element.get_attribute("href")
                if not href or href in seen_urls:
                    continue
                seen_urls.add(href)
                
                name = (await element.inner_text()).strip()
                
                if name and "view.php?id=" in href:
                    course_id = href.split("id=")[1].split("&")[0] if "id=" in href else ""
                    
                    courses.append({
                        "name": name,
                        "url": href if href.startswith("http") else CONFIG["base_url"] + href,
                        "id": course_id
                    })
            except:
                continue
        
        # Remove duplicates
        unique_courses = []
        urls_seen = set()
        for course in courses:
            if course["url"] not in urls_seen:
                urls_seen.add(course["url"])
                unique_courses.append(course)
        
        log(f"Found {len(unique_courses)} courses", "SUCCESS")
        return unique_courses
    
    except Exception as e:
        log(f"Error discovering courses: {e}", "ERROR")
        return []

async def discover_activities(page: Page, course_name: str, course_id: str) -> List[Dict]:
    """Find all activities in a course"""
    
    try:
        await asyncio.sleep(1)
        
        # Expand sections
        try:
            buttons = await page.locator('.card-header a[data-toggle="collapse"]').all()
            for btn in buttons:
                try:
                    await btn.click(timeout=800)
                    await asyncio.sleep(0.2)
                except:
                    pass
        except:
            pass
        
        await asyncio.sleep(0.8)
        
        # Find activities
        activity_elements = await page.locator('a[href*="/mod/"]').all()
        
        activities = []
        seen_urls = set()
        
        for element in activity_elements:
            try:
                href = await element.get_attribute("href")
                if not href or href in seen_urls or "/mod/" not in href:
                    continue
                
                seen_urls.add(href)
                
                name = (await element.inner_text()).strip()
                if not name:
                    continue
                
                activity_type = "unknown"
                for pattern in ["/mod/page/", "/mod/url/", "/mod/quiz/", "/mod/assign/", "/mod/forum/", "/mod/book/"]:
                    if pattern in href:
                        activity_type = pattern.split("/")[2]
                        break
                
                should_skip = any(pattern in href for pattern in CONFIG["skip_patterns"])
                
                # Check if already completed
                is_completed = progress.is_activity_completed(course_id, href)
                
                activities.append({
                    "name": name,
                    "url": href if href.startswith("http") else CONFIG["base_url"] + href,
                    "type": activity_type,
                    "should_skip": should_skip,
                    "is_completed": is_completed
                })
            except:
                continue
        
        return activities
    
    except Exception as e:
        log(f"Error discovering activities: {e}", "ERROR")
        return []

# ============================================================================
# ACTIVITY PROCESSORS WITH RETRY LOGIC
# ============================================================================

async def mark_complete(page: Page) -> bool:
    """Mark activity as complete"""
    try:
        selectors = [
            'button[data-action="toggle-manual-completion"]',
            '.manual-completion-toggle',
            'input[type="checkbox"][name="completionstate"]'
        ]
        
        for selector in selectors:
            try:
                element = page.locator(selector).first
                if await element.count() > 0:
                    classes = await element.get_attribute("class") or ""
                    if "complete" in classes.lower():
                        return True
                    
                    await element.click(timeout=2000)
                    await asyncio.sleep(0.5)
                    return True
            except:
                continue
        
        return False
    except:
        return False

async def process_page(page: Page, activity: Dict, course_name: str, course_id: str):
    """Process a page activity with retry"""
    try:
        await page.goto(activity["url"], wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(random.uniform(*CONFIG["page_load_wait"]))
        
        await human_scroll(page)
        await asyncio.sleep(random.uniform(*CONFIG["content_view_time"]))
        await mark_complete(page)
        
        stats.log_completed(course_name, activity["name"], "page")
        progress.mark_activity_completed(course_id, activity["url"])
        
    except Exception as e:
        raise Exception(f"Page error: {e}")

async def process_url(page: Page, activity: Dict, course_name: str, course_id: str):
    """Process a URL activity with retry"""
    try:
        await page.goto(activity["url"], wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(random.uniform(*CONFIG["page_load_wait"]))
        
        # Try to open external link in new tab
        try:
            async with page.context.expect_page(timeout=5000) as new_page_info:
                link = page.locator('.urlworkaround a, a[target="_blank"]').first
                if await link.count() > 0:
                    await link.click()
            new_page = await new_page_info.value
            await asyncio.sleep(1.5)
            await new_page.close()
        except:
            pass
        
        await asyncio.sleep(random.uniform(*CONFIG["content_view_time"]))
        await mark_complete(page)
        
        stats.log_completed(course_name, activity["name"], "url")
        progress.mark_activity_completed(course_id, activity["url"])
        
    except Exception as e:
        raise Exception(f"URL error: {e}")

async def process_forum(page: Page, activity: Dict, course_name: str, course_id: str):
    """Process a forum activity with retry"""
    try:
        await page.goto(activity["url"], wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(random.uniform(*CONFIG["page_load_wait"]))
        
        await human_scroll(page)
        await asyncio.sleep(random.uniform(*CONFIG["content_view_time"]))
        await mark_complete(page)
        
        stats.log_completed(course_name, activity["name"], "forum")
        progress.mark_activity_completed(course_id, activity["url"])
        
    except Exception as e:
        raise Exception(f"Forum error: {e}")

async def process_activity_with_retry(page: Page, activity: Dict, course_name: str, course_id: str) -> bool:
    """Process activity with retry logic"""
    
    # Skip if already completed
    if activity["is_completed"]:
        log(f"  ✅ Already done: {activity['name'][:50]}", "SUCCESS")
        return True
    
    # Skip quizzes/assignments
    if activity["should_skip"]:
        if "quiz" in activity["type"]:
            stats.log_skipped(course_name, activity["name"], "quiz")
        elif "assign" in activity["type"]:
            stats.log_skipped(course_name, activity["name"], "assignment")
        return True
    
    # Process with retries
    for attempt in range(1, CONFIG["max_retries"] + 1):
        try:
            if activity["type"] == "page":
                await process_page(page, activity, course_name, course_id)
            elif activity["type"] == "url":
                await process_url(page, activity, course_name, course_id)
            elif activity["type"] == "forum":
                await process_forum(page, activity, course_name, course_id)
            else:
                await process_page(page, activity, course_name, course_id)
            
            return True  # Success
            
        except Exception as e:
            if attempt < CONFIG["max_retries"]:
                log(f"  ⚠️  Attempt {attempt} failed, retrying...", "WARNING")
                await asyncio.sleep(1)
            else:
                error_msg = f"{activity['type']} error in {course_name}: {activity['name']}"
                log(f"  ❌ Failed after {CONFIG['max_retries']} attempts", "ERROR")
                stats.log_error(error_msg)
                progress.mark_activity_failed(course_id, activity["url"], str(e))
                await take_screenshot(page, f"error_{course_id}_{activity['type']}")
                return False
    
    return False

# ============================================================================
# PARALLEL PROCESSING
# ============================================================================

async def process_activities_parallel(context: BrowserContext, activities: List[Dict], course_name: str, course_id: str):
    """Process multiple activities in parallel"""
    
    # Filter activities to process
    to_process = [a for a in activities if not a["is_completed"] and not a["should_skip"]]
    
    if not to_process:
        log("  All activities already completed!", "SUCCESS")
        return
    
    log(f"  Processing {len(to_process)} activities in parallel ({CONFIG['parallel_tabs']} tabs)...", "PARALLEL")
    
    # Process in batches
    for i in range(0, len(to_process), CONFIG["parallel_tabs"]):
        batch = to_process[i:i + CONFIG["parallel_tabs"]]
        
        # Create pages for this batch
        pages = []
        for _ in batch:
            page = await context.new_page()
            pages.append(page)
        
        # Process batch in parallel
        tasks = []
        for idx, (page, activity) in enumerate(zip(pages, batch)):
            log(f"  [{i+idx+1}/{len(to_process)}] {activity['type']}: {activity['name'][:40]}...", "PROGRESS")
            task = process_activity_with_retry(page, activity, course_name, course_id)
            tasks.append(task)
        
        # Wait for all tasks in batch
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Close pages
        for page in pages:
            await page.close()
        
        # Small delay between batches
        await random_delay(*CONFIG["between_activities"])
    
    log(f"  ✅ Batch completed!", "SUCCESS")

# ============================================================================
# COURSE PROCESSOR
# ============================================================================

async def process_course(context: BrowserContext, course: Dict):
    """Process all activities in a course"""
    log("\n" + "#" * 70, "COURSE")
    log(f"📚 PROCESSING: {course['name']}", "COURSE")
    log("#" * 70 + "\n", "COURSE")
    
    # Create a page for navigation
    page = await context.new_page()
    
    try:
        # Navigate to course
        await page.goto(course["url"], wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)
        
        # Discover activities
        activities = await discover_activities(page, course["name"], course["id"])
        
        if not activities:
            log("No activities found", "WARNING")
            await page.close()
            return
        
        # Update progress tracking
        course_progress = progress.get_course_progress(course["id"])
        course_progress["name"] = course["name"]
        course_progress["total_activities"] = len([a for a in activities if not a["should_skip"]])
        
        # Count stats
        to_process = [a for a in activities if not a["should_skip"] and not a["is_completed"]]
        already_done = [a for a in activities if a["is_completed"]]
        to_skip = [a for a in activities if a["should_skip"]]
        
        log(f"Found {len(activities)} activities:", "INFO")
        log(f"  ✅ Already done: {len(already_done)}", "SUCCESS")
        log(f"  ⏳ To process: {len(to_process)}", "INFO")
        log(f"  ⏭️  To skip: {len(to_skip)}\n", "SKIP")
        
        # Process activities in parallel
        await process_activities_parallel(context, activities, course["name"], course["id"])
        
        # Update course status
        completion_pct = progress.get_course_completion_percent(course["id"])
        if completion_pct >= 100:
            course_progress["status"] = "completed"
        elif completion_pct > 0:
            course_progress["status"] = "in_progress"
        progress.save()
        
        stats.courses_processed += 1
        
        log(f"\n✅ Course {int(completion_pct)}% complete!\n", "SUCCESS")
        
    except Exception as e:
        log(f"Error processing course: {e}", "ERROR")
        stats.log_error(f"Course error: {course['name']}")
    
    finally:
        await page.close()
        await random_delay(*CONFIG["between_courses"])

# ============================================================================
# REPORT GENERATOR
# ============================================================================

def generate_report():
    """Generate final report"""
    log("\n" + "=" * 70, "SUCCESS")
    log("📊 AUTOMATION REPORT", "SUCCESS")
    log("=" * 70, "SUCCESS")
    log(f"⏱️  Duration: {stats.get_duration()}", "INFO")
    log(f"📚 Courses Processed: {stats.courses_processed}", "INFO")
    log(f"✅ Activities Completed: {stats.activities_completed}", "SUCCESS")
    log(f"⏭️  Activities Skipped: {stats.activities_skipped}", "INFO")
    log(f"❌ Activities Failed: {stats.activities_failed}", "ERROR")
    
    if stats.quizzes_found:
        log(f"\n📝 Quizzes to Complete Manually: {len(stats.quizzes_found)}", "QUIZ")
        for item in stats.quizzes_found[:5]:
            log(f"   {item['course']}: {item['activity'][:50]}", "INFO")
        if len(stats.quizzes_found) > 5:
            log(f"   ... and {len(stats.quizzes_found) - 5} more", "INFO")
    
    if stats.assignments_found:
        log(f"\n📋 Assignments to Complete Manually: {len(stats.assignments_found)}", "ASSIGNMENT")
        for item in stats.assignments_found[:5]:
            log(f"   {item['course']}: {item['activity'][:50]}", "INFO")
        if len(stats.assignments_found) > 5:
            log(f"   ... and {len(stats.assignments_found) - 5} more", "INFO")
    
    if stats.errors:
        log(f"\n❌ Errors Encountered: {len(stats.errors)}", "ERROR")
        for error in stats.errors[:5]:
            log(f"   {error['message'][:70]}", "ERROR")
        if len(stats.errors) > 5:
            log(f"   ... and {len(stats.errors) - 5} more (check miva_progress.json)", "INFO")
    
    log("\n" + "=" * 70, "SUCCESS")
    
    # Save detailed report
    try:
        report_file = f"miva_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "duration": stats.get_duration(),
                    "courses_processed": stats.courses_processed,
                    "activities_completed": stats.activities_completed,
                    "activities_skipped": stats.activities_skipped,
                    "activities_failed": stats.activities_failed
                },
                "quizzes": stats.quizzes_found,
                "assignments": stats.assignments_found,
                "errors": stats.errors,
                "completed_activities": stats.completed_activities
            }, f, indent=2, ensure_ascii=False)
        log(f"📄 Detailed report saved: {report_file}", "SUCCESS")
    except Exception as e:
        log(f"Could not save report: {e}", "WARNING")

# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main automation"""
    log("\n" + "=" * 70, "INFO")
    log("🚀 MIVA LMS ULTIMATE AUTOMATION", "SUCCESS")
    log("=" * 70, "INFO")
    log("Features: Reconnaissance | Smart Resume | Parallel Processing", "INFO")
    log("Speed: Balanced-Fast | Tabs: 4 parallel", "INFO")
    log("=" * 70 + "\n", "INFO")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=CONFIG["headless"],
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='Africa/Lagos'
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        
        page = await context.new_page()
        auth = AuthManager(context)
        
        # Load cookies and check login
        await auth.load_cookies()
        
        try:
            await page.goto(CONFIG["courses_url"], wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)
            
            if not await auth.check_logged_in(page):
                log("❌ Not logged in! Please run test_login.py first", "ERROR")
                await browser.close()
                return
            
            log("✅ Logged in successfully!", "SUCCESS")
        except Exception as e:
            log(f"❌ Login check failed: {e}", "ERROR")
            await browser.close()
            return
        
        # Discover courses
        courses = await discover_courses(page)
        
        if not courses:
            log("No courses found", "ERROR")
            await browser.close()
            return
        
        # Run reconnaissance
        if CONFIG["run_reconnaissance"]:
            recon_data = await run_reconnaissance(page, courses)
        
        # Prioritize courses (in_progress > not_started > completed)
        courses = progress.prioritize_courses(courses)
        
        log("🔄 Course Processing Order (Smart Resume):", "RESUME")
        for i, course in enumerate(courses, 1):
            completion = progress.get_course_completion_percent(course["id"])
            status_icon = "✅" if completion >= 100 else "🔄" if completion > 0 else "⏳"
            log(f"  {i}. {status_icon} {course['name'][:50]} ({int(completion)}% done)", "INFO")
        log("", "INFO")
        
        # Process courses
        for course in courses:
            completion = progress.get_course_completion_percent(course["id"])
            
            # Skip completed courses
            if completion >= 100:
                log(f"⏭️  Skipping {course['name']} (100% complete)", "SKIP")
                continue
            
            await process_course(context, course)
        
        # Generate report
        generate_report()
        
        log("\n🎉 AUTOMATION COMPLETE! 🎉\n", "SUCCESS")
        
        if not CONFIG["headless"]:
            await asyncio.sleep(10)
        
        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\n\nAutomation interrupted", "WARNING")
        generate_report()
    except Exception as e:
        log(f"\n\nFatal error: {e}", "ERROR")
        generate_report()
