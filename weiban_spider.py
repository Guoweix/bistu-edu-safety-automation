"""
微伴学习平台爬虫脚本
使用 Playwright 框架，支持手动登录
由于网站不保持 Cookie 登录状态，每次运行需要重新登录
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, Playwright
from typing import Optional, Dict, List
import time


class WeibanSpider:
    def __init__(self, headless: bool = False, login_timeout: int = 120):
        """
        初始化爬虫
        :param headless: 是否使用无头模式（True=后台运行，False=显示浏览器）
        :param login_timeout: 等待登录的超时时间（秒）
        """
        self.headless = headless
        self.login_timeout = login_timeout
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright: Optional[Playwright] = None
        
    async def init_browser(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        
        # 启动浏览器，配置反检测参数
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',  # 禁用自动化控制特征
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        # 创建浏览器上下文，设置视口和用户代理
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN'
        )
        
        # 创建新页面
        self.page = await context.new_page()
        
        # 注入反检测脚本
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        print("✅ 浏览器初始化成功")

    
    async def wait_for_login(self):
        """
        打开登录页面并等待用户完成登录
        """
        if not self.browser:
            await self.init_browser()
        
        print("🌐 正在打开微伴学习平台...")
        await self.page.goto('https://weiban.mycourse.cn/#/', wait_until='domcontentloaded')
        
        # 等待页面加载
        await asyncio.sleep(2)
        
        print("\n" + "="*70)
        print("📢 请在浏览器中完成登录操作")
        print("📢 脚本将自动检测登录状态...")
        print("="*70 + "\n")
        
        # 自动检测登录状态
        start_time = time.time()
        check_interval = 2  # 每2秒检查一次
        
        while time.time() - start_time < self.login_timeout:
            is_logged = await self.check_login_status()
            
            if is_logged:
                print("\n✅ 检测到登录成功！")
                return True
            
            # 等待一段时间再检查
            await asyncio.sleep(check_interval)
            elapsed = int(time.time() - start_time)
            remaining = self.login_timeout - elapsed
            print(f"⏳ 等待登录中... (剩余 {remaining} 秒)", end='\r')
        
        print("\n⚠️  登录超时，请重新运行脚本")
        return False
    
    async def check_login_status(self) -> bool:
        """
        检查是否已登录
        通过多种方式判断登录状态
        """
        try:
            current_url = self.page.url
            
            # 方法1: 检查 URL 变化（登录后通常会跳转）
            if 'login' in current_url.lower():
                return False
            
            # 方法2: 检查页面是否有登录框（如果有登录框说明未登录）
            try:
                login_form = await self.page.query_selector('input[type="password"]')
                if login_form:
                    return False
            except:
                pass
            
            # 方法3: 检查 localStorage 或 sessionStorage 中的登录信息
            storage_check = await self.page.evaluate("""
                () => {
                    // 检查所有可能的存储位置
                    const hasToken = !!(
                        localStorage.getItem('token') || 
                        localStorage.getItem('userInfo') ||
                        localStorage.getItem('user') ||
                        localStorage.getItem('Authorization') ||
                        sessionStorage.getItem('token') ||
                        sessionStorage.getItem('userInfo') ||
                        sessionStorage.getItem('user') ||
                        sessionStorage.getItem('Authorization')
                    );
                    
                    // 检查是否有用户相关的数据
                    const localKeys = Object.keys(localStorage);
                    const sessionKeys = Object.keys(sessionStorage);
                    const hasUserData = localKeys.some(k => 
                        k.includes('user') || k.includes('token') || k.includes('auth')
                    ) || sessionKeys.some(k => 
                        k.includes('user') || k.includes('token') || k.includes('auth')
                    );
                    
                    return hasToken || hasUserData;
                }
            """)
            
            # 方法4: 检查页面特定元素（需要根据实际页面调整）
            # 尝试查找用户信息或个人中心相关元素
            try:
                user_element = await self.page.query_selector('.user-info, .user-name, .avatar, [class*="user"], [class*="personal"]')
                if user_element:
                    return True
            except:
                pass
            
            # 方法5: 检查 Cookie 中是否有会话信息
            cookies = await self.page.context.cookies()
            has_session = any(
                'session' in c['name'].lower() or 
                'token' in c['name'].lower() or
                'auth' in c['name'].lower()
                for c in cookies
            )
            
            # 综合判断：有存储信息或会话 Cookie 就认为已登录
            return storage_check or has_session
            
        except Exception as e:
            print(f"⚠️  检查登录状态时出错: {e}")
            return False
    
    async def get_user_info(self) -> Dict:
        """
        获取当前登录用户信息（如果页面上有的话）
        """
        try:
            user_info = await self.page.evaluate("""
                () => {
                    // 尝试从 localStorage 或 sessionStorage 获取用户信息
                    const userInfo = localStorage.getItem('userInfo') || 
                                    sessionStorage.getItem('userInfo');
                    if (userInfo) {
                        try {
                            return JSON.parse(userInfo);
                        } catch {
                            return {};
                        }
                    }
                    return {};
                }
            """)
            return user_info
        except Exception as e:
            print(f"⚠️  获取用户信息失败: {e}")
            return {}
        
    async def get_page_content(self) -> str:
        """获取当前页面内容"""
        if not self.page:
            return ""
        return await self.page.content()
    
    async def screenshot(self, filename: str = "screenshot.png"):
        """截图保存"""
        if not self.page:
            print("❌ 页面未初始化")
            return
        await self.page.screenshot(path=filename, full_page=True)
        print(f"📸 截图已保存: {filename}")
    
    async def save_state(self, filename: str = "browser_state.json"):
        """
        保存浏览器状态（Cookie、localStorage 等）
        虽然这个网站可能不支持 Cookie 登录，但保存状态供调试用
        """
        if not self.page:
            return
        
        try:
            # 获取所有 Cookie
            cookies = await self.page.context.cookies()
            
            # 获取 localStorage 和 sessionStorage
            storage = await self.page.evaluate("""
                () => {
                    return {
                        localStorage: {...localStorage},
                        sessionStorage: {...sessionStorage}
                    };
                }
            """)
            
            state = {
                'cookies': cookies,
                'storage': storage,
                'url': self.page.url
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            print(f"📦 浏览器状态已保存到 {filename}")
        except Exception as e:
            print(f"⚠️  保存状态失败: {e}")
    
    async def close(self):
        """关闭浏览器和 Playwright"""
        if self.browser:
            await self.browser.close()
            print("👋 浏览器已关闭")
        
        if self.playwright:
            await self.playwright.stop()


async def main():
    """主函数 - 演示如何使用爬虫"""
    # 创建爬虫实例
    # headless=False: 显示浏览器窗口，方便手动登录
    # login_timeout: 等待登录的超时时间（秒）
    spider = WeibanSpider(headless=False, login_timeout=120)
    
    try:
        # 初始化浏览器
        await spider.init_browser()
        
        # 等待用户登录
        login_success = await spider.wait_for_login()
        
        if not login_success:
            print("❌ 登录失败或超时")
            return
        
        # 获取用户信息（可选）
        user_info = await spider.get_user_info()
        if user_info:
            print(f"👤 用户信息: {user_info}")
        
        # 等待页面完全加载
        print("\n⏳ 等待页面加载...")
        await asyncio.sleep(3)
        
        # 截图保存当前页面
        await spider.screenshot("weiban_logged_in.png")
        
        # ========== 在这里添加你的爬取逻辑 ==========
        
        # 示例1: 获取页面标题
        title = await spider.page.title()
        print(f"📄 页面标题: {title}")
        
        # 步骤1: 点击实验室标题图片
        try:
            print("\n🖱️  [步骤1] 正在点击实验室图片...")
            
            # 等待图片加载完成
            await spider.page.wait_for_selector('img[src*="lab-title-thin"]', timeout=10000)
            await spider.page.click('img[src*="lab-title-thin"]')
            print("✅ 图片点击成功")
            
            # 等待页面跳转或响应
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"⚠️  点击图片失败: {e}")
            try:
                # 备用方法
                await spider.page.click('img[data-v-fa5cdbae][alt=""]')
                print("✅ 使用备用方法点击成功")
            except Exception as e2:
                print(f"⚠️  备用方法也失败: {e2}")
        
        # 步骤2: 点击课程标题
        try:
            print("\n🖱️  [步骤2] 正在点击课程标题...")
            
            # 等待课程标题出现
            await spider.page.wait_for_selector('h5.block-title', timeout=10000)
            
            # 方法1: 使用文本内容精确匹配
            await spider.page.click('h5.block-title:has-text("2025级硕士生实验室安全教育（信通学院）")')
            print("✅ 课程标题点击成功")
            
            # 等待页面响应
            await asyncio.sleep(3)
            
        except Exception as e:
            print(f"⚠️  点击课程标题失败: {e}")
            # 备用方法
            try:
                # 方法2: 使用 CSS 选择器 + 文本部分匹配
                await spider.page.click('h5.block-title:has-text("实验室安全教育")')
                print("✅ 使用备用方法点击成功")
            except Exception as e2:
                print(f"⚠️  备用方法也失败: {e2}")
                # 方法3: 使用 XPath
                try:
                    await spider.page.click('xpath=//h5[@class="block-title" and contains(text(), "实验室安全教育")]')
                    print("✅ 使用 XPath 点击成功")
                except Exception as e3:
                    print(f"⚠️  所有方法均失败: {e3}")
                    return
        
        # 步骤3: 遍历并完成未完成的课程模块
        try:
            print("\n📚 [步骤3] 开始处理课程模块...")
            
            # 等待课程列表加载
            await spider.page.wait_for_selector('.van-collapse-item', timeout=10000)
            await asyncio.sleep(2)
            
            # 获取所有课程模块
            modules = await spider.page.query_selector_all('.van-collapse-item')
            total_modules = len(modules)
            print(f"📊 找到 {total_modules} 个课程模块")
            
            completed_count = 0
            
            # 使用索引遍历模块，避免 DOM 刷新问题
            module_index = 0
            while module_index < total_modules:
                try:
                    # 每次循环都重新获取模块列表
                    modules = await spider.page.query_selector_all('.van-collapse-item')
                    
                    if module_index >= len(modules):
                        print(f"ℹ️  已处理完所有模块")
                        break
                    
                    module = modules[module_index]
                    
                    # 获取模块标题
                    title_elem = await module.query_selector('.text')
                    module_title = await title_elem.text_content() if title_elem else "未知模块"
                    
                    # 获取完成情况
                    count_elem = await module.query_selector('.count')
                    count_text = await count_elem.text_content() if count_elem else "0/0"
                    
                    # 解析完成情况 (格式: "已完成/总数")
                    count_text = count_text.strip()
                    if '/' in count_text:
                        finished, total = count_text.split('/')
                        finished = int(finished)
                        total = int(total)
                    else:
                        finished, total = 0, 0
                    
                    print(f"\n{'='*60}")
                    print(f"📖 [{module_index + 1}/{total_modules}] 模块: {module_title}")
                    print(f"📊 进度: {finished}/{total}")
                    
                    # 判断是否已完成
                    if finished >= total and total > 0:
                        print(f"✅ 该模块已完成，跳过")
                        module_index += 1
                        continue
                    
                    print(f"🎯 该模块未完成，准备处理...")
                    
                    # 点击展开模块
                    title_button = await module.query_selector('.van-collapse-item__title')
                    if title_button:
                        await title_button.click()
                        print(f"📂 已展开模块")
                        await asyncio.sleep(2)
                    
                    # 获取该模块下的所有课程项
                    course_items = await module.query_selector_all('.img-texts-item')
                    
                    if not course_items:
                        print(f"⚠️  未找到课程项，跳过")
                        continue
                    
                    print(f"📝 找到 {len(course_items)} 个课程项")
                    
                    # 【重构】使用死循环,每次查找第一个未完成的课程
                    while True:
                        try:
                            # 每次循环都重新获取模块和课程列表（防止 DOM 刷新）
                            modules = await spider.page.query_selector_all('.van-collapse-item')
                            if module_index >= len(modules):
                                print(f"  ⚠️  模块索引超出范围，跳出循环")
                                break
                            module = modules[module_index]
                            
                            # 【关键修复】确保模块已展开
                            module_class = await module.get_attribute('class')
                            is_expanded = 'van-collapse-item--expanded' in (module_class or '')
                            
                            if not is_expanded:
                                print(f"  🔓 模块未展开，正在展开...")
                                title_button = await module.query_selector('.van-collapse-item__title')
                                if title_button:
                                    await title_button.click()
                                    await asyncio.sleep(2)
                                    print(f"  ✅ 模块已展开")
                                    
                                    # 重新获取模块（因为点击后 DOM 可能刷新）
                                    modules = await spider.page.query_selector_all('.van-collapse-item')
                                    if module_index >= len(modules):
                                        break
                                    module = modules[module_index]
                            
                            # 重新获取课程项列表
                            course_items = await module.query_selector_all('.img-texts-item')
                            print(f"  📚 当前模块有 {len(course_items)} 个课程项")
                            
                            # 查找第一个未完成的课程
                            item = None
                            item_title = None
                            item_position = -1
                            
                            for idx, course_item in enumerate(course_items):
                                item_class = await course_item.get_attribute('class')
                                is_passed = 'passed' in item_class if item_class else False
                                
                                if not is_passed:
                                    # 找到第一个未完成的课程
                                    item = course_item
                                    item_position = idx + 1
                                    item_title_elem = await course_item.query_selector('.title')
                                    item_title = await item_title_elem.text_content() if item_title_elem else "未知课程"
                                    break
                            
                            # 如果没有找到未完成的课程，退出循环
                            if item is None:
                                print(f"  ✅ 当前模块所有课程已完成！")
                                break
                            
                            print(f"\n  🎬 [{item_position}/{len(course_items)}] 开始学习: {item_title}")
                            
                            # 【修复】点击课程项 - 使用更可靠的方法
                            try:
                                # 先检查元素状态
                                is_visible = await item.is_visible()
                                print(f"  🔍 元素可见性: {is_visible}")
                                
                                # 滚动到元素位置
                                print(f"  📜 滚动到元素位置...")
                                await item.scroll_into_view_if_needed()
                                await asyncio.sleep(1)
                                
                                # 方法1: 尝试直接点击
                                try:
                                    await item.click(timeout=5000)
                                    print(f"  🖱️  已点击课程（方法1）")
                                except Exception as e1:
                                    print(f"  ⚠️  方法1失败: {str(e1)[:100]}")
                                    
                                    # 方法2: 使用 force 点击（忽略可见性检查）
                                    try:
                                        await item.click(force=True)
                                        print(f"  🖱️  已点击课程（方法2: force）")
                                    except Exception as e2:
                                        print(f"  ⚠️  方法2失败: {str(e2)[:100]}")
                                        
                                        # 方法3: 通过 JavaScript 点击
                                        print(f"  🔄 尝试 JavaScript 点击...")
                                        await item.evaluate('element => element.click()')
                                        print(f"  🖱️  已点击课程（方法3: JS）")
                                
                            except Exception as e:
                                print(f"  ❌ 所有点击方法都失败: {e}")
                                raise
                            
                            # 等待页面跳转和加载
                            print(f"  ⏳ 等待页面跳转...")
                            await asyncio.sleep(3)
                            
                            # 等待页面完全加载
                            try:
                                await spider.page.wait_for_load_state('domcontentloaded', timeout=10000)
                                print(f"  ✅ 页面 DOM 加载完成")
                            except Exception as e:
                                print(f"  ⚠️  等待页面加载超时: {e}")
                            
                            # 等待 iframe 加载
                            print(f"  🔍 查找 iframe...")
                            iframe = None
                            try:
                                # 不等待 iframe 可见，直接获取所有 frames
                                # 因为页面可能有多个占位符 iframe，等待可见会超时
                                print(f"  🔍 检查页面中的 iframe...")
                                
                                # 先等待一下，让 iframe 有时间加载
                                await asyncio.sleep(3)
                                
                                # 获取所有 iframe
                                frames = spider.page.frames
                                print(f"  📄 页面共有 {len(frames)} 个 frame")
                                
                                # 打印所有 frame 的 URL 用于调试
                                for idx, frame in enumerate(frames):
                                    frame_url = frame.url
                                    frame_name = frame.name
                                    print(f"    Frame {idx}: {frame_url[:100] if len(frame_url) > 100 else frame_url}")
                                    if frame_name:
                                        print(f"             Name: {frame_name}")
                                
                                # 查找包含课程内容的 iframe（通过 URL 特征）
                                # 优先级：mcwk.mycourse.cn > 其他条件
                                for frame in frames:
                                    frame_url = frame.url
                                    # 跳过空白或占位符 iframe
                                    if not frame_url or frame_url == 'about:blank' or 'javascript:' in frame_url:
                                        continue
                                    
                                    # 【最高优先级】检查是否包含 mcwk.mycourse.cn 域名
                                    # 这是真正的课程内容iframe
                                    if 'mcwk.mycourse.cn' in frame_url:
                                        iframe = frame
                                        print(f"  ✅ 找到课程 iframe (mcwk域名): {frame_url[:80]}...")
                                        break
                                
                                # 如果没找到 mcwk 域名的，再尝试其他特征
                                if not iframe:
                                    for frame in frames:
                                        frame_url = frame.url
                                        if not frame_url or frame_url == 'about:blank' or 'javascript:' in frame_url:
                                            continue
                                        
                                        # 跳过 weiban.mycourse.cn 主域名（那是外层页面）
                                        if 'weiban.mycourse.cn' in frame_url:
                                            continue
                                        
                                        # 检查是否包含 course 关键字
                                        if '/course/' in frame_url.lower():
                                            iframe = frame
                                            print(f"  ℹ️  找到备选 iframe (course路径): {frame_url[:80]}...")
                                            break
                                
                                # 如果还是没找到，尝试找第一个有实际内容的 frame
                                if not iframe:
                                    for frame in frames:
                                        frame_url = frame.url
                                        # 跳过主页面和占位符
                                        if frame_url and frame_url != spider.page.url and 'javascript:' not in frame_url and frame_url != 'about:blank':
                                            iframe = frame
                                            print(f"  ℹ️  使用第一个有效 iframe: {frame_url[:80]}...")
                                            break
                                
                            except Exception as e:
                                print(f"  ⚠️  查找 iframe 失败: {e}")
                                import traceback
                                traceback.print_exc()
                            
                            # 如果没有找到 iframe，使用主页面
                            if not iframe:
                                print(f"  ❌ 未找到有效 iframe，使用主页面 (这可能导致找不到按钮)")
                                iframe = spider.page.main_frame
                            else:
                                print(f"  ✅ 最终使用的 iframe URL: {iframe.url[:100]}")
                            
                            # 等待 iframe 内容加载
                            print(f"  ⏳ 等待 iframe 内容加载...")
                            await asyncio.sleep(3)
                            
                            # 等待网络请求完成
                            try:
                                await spider.page.wait_for_load_state('networkidle', timeout=10000)
                                print(f"  ✅ 网络请求完成")
                            except Exception as e:
                                print(f"  ⚠️  等待网络空闲超时: {e}")
                            
                            # 等待动画播放完成
                            print(f"  🎬 等待页面动画完成...")
                            animation_wait = 5  # 等待5秒让动画播放完成
                            for remaining in range(animation_wait, 0, -1):
                                print(f"     等待动画: {remaining} 秒", end='\r')
                                await asyncio.sleep(1)
                            print()  # 换行
                            
                            # 判断课程类型：视频课程 vs 交互式课程
                            print(f"  🔍 检测课程类型...")
                            is_video_course = False
                            try:
                                # 检查是否有"建议在wifi环境下观看"的提示
                                wifi_tip = await iframe.query_selector('p.txt-des:has-text("建议在wifi环境下观看")')
                                if wifi_tip:
                                    is_video_course = True
                                    print(f"  📹 检测到视频课程（无需点击开始按钮）")
                                else:
                                    print(f"  🎮 检测到交互式课程（需要点击开始按钮）")
                            except Exception as e:
                                print(f"  ⚠️  课程类型检测失败，默认为交互式: {e}")
                            
                            # 根据课程类型处理
                            start_btn_clicked = False
                            
                            if is_video_course:
                                # 视频课程：直接跳过点击开始按钮的步骤
                                print(f"  ⏭️  视频课程，跳过点击开始按钮")
                                start_btn_clicked = True  # 标记为已处理
                            else:
                                # 交互式课程：需要点击开始按钮
                                print(f"  🔍 在 iframe 中查找开始按钮...")
                                
                                try:
                                    # 方法1: 在 iframe 中查找 btn-start 按钮（优先）
                                    print(f"  ⏳ 等待开始按钮出现（最多20秒）...")
                                    await iframe.wait_for_selector('.btn-start, a.btn-start', timeout=20000, state='visible')
                                    print(f"  ✅ 找到开始按钮 (btn-start)")
                                    
                                    # 再等待一下确保按钮完全可点击（动画结束）
                                    await asyncio.sleep(2)
                                    
                                    # 确保按钮可点击状态
                                    is_visible = await iframe.is_visible('.btn-start')
                                    print(f"  🔍 按钮可见性: {is_visible}")
                                    
                                    # 在 iframe 中点击开始按钮
                                    print(f"  🖱️  点击开始按钮...")
                                    await iframe.click('.btn-start', timeout=5000)
                                    print(f"  ✅ 已点击开始按钮")
                                    start_btn_clicked = True
                                    
                                    # 等待 finishWxCourse 函数加载
                                    print(f"  ⏳ 等待函数加载...")
                                    await asyncio.sleep(5)
                                    
                                except Exception as e:
                                    print(f"  ⚠️  方法1失败: {e}")
                                    
                                    # 方法2: 尝试通过 img 的 src 属性定位
                                    try:
                                        print(f"  🔄 尝试通过图片定位...")
                                        await iframe.wait_for_selector('img[src*="btn-start"]', timeout=10000)
                                        # 点击包含该图片的父元素
                                        await iframe.click('a:has(img[src*="btn-start"])')
                                        print(f"  ✅ 使用图片定位点击成功")
                                        start_btn_clicked = True
                                        await asyncio.sleep(5)
                                        
                                    except Exception as e2:
                                        print(f"  ⚠️  方法2失败: {e2}")
                                        
                                        # 方法3: 尝试 pri-start-btn
                                        try:
                                            print(f"  🔄 尝试 pri-start-btn...")
                                            await iframe.click('.pri-start-btn')
                                            print(f"  ✅ 使用 pri-start-btn 点击成功")
                                            start_btn_clicked = True
                                            await asyncio.sleep(5)
                                            
                                        except Exception as e3:
                                            print(f"  ⚠️  方法3失败: {e3}")
                                            
                                            # 方法4: 尝试查找所有可能的开始按钮
                                            try:
                                                print(f"  🔄 尝试查找所有按钮...")
                                                # 在 iframe 中使用 XPath 查找
                                                start_elems = await iframe.query_selector_all('a[class*="start"], button[class*="start"]')
                                                if start_elems:
                                                    await start_elems[0].click()
                                                    print(f"  ✅ 使用通用方法点击成功")
                                                    start_btn_clicked = True
                                                    await asyncio.sleep(5)
                                                else:
                                                    print(f"  ❌ 未找到任何开始按钮")
                                                
                                            except Exception as e4:
                                                print(f"  ❌ 所有方法均失败: {e4}")
                            
                            if not start_btn_clicked:
                                print(f"  ⚠️  未能点击开始按钮，尝试继续...")
                            
                            # 在 iframe 中检查 finishWxCourse 函数是否存在
                            print(f"  🔍 检查 finishWxCourse() 函数是否可用...")
                            func_exists = await iframe.evaluate("""
                                () => typeof finishWxCourse === 'function'
                            """)
                            
                            if not func_exists:
                                print(f"  ⚠️  finishWxCourse() 函数不存在，再等待 10 秒...")
                                await asyncio.sleep(10)
                                # 再次检查
                                func_exists = await iframe.evaluate("""
                                    () => typeof finishWxCourse === 'function'
                                """)
                            
                            if func_exists:
                                print(f"  ✅ finishWxCourse() 函数已就绪")
                                
                                # 在 iframe 中执行 finishWxCourse() 函数
                                print(f"  ⚡ 执行 finishWxCourse() 函数...")
                                try:
                                    result = await iframe.evaluate('finishWxCourse()')
                                    print(f"  ✅ finishWxCourse() 执行完成，返回: {result}")
                                except Exception as e:
                                    print(f"  ⚠️  执行 finishWxCourse() 失败: {e}")
                                    import traceback
                                    traceback.print_exc()
                            else:
                                print(f"  ❌ finishWxCourse() 函数仍不可用")
                                # 打印 iframe 信息用于调试
                                try:
                                    frame_info = await iframe.evaluate("""
                                        () => {
                                            return {
                                                title: document.title,
                                                url: window.location.href,
                                                hasFunctions: Object.keys(window).filter(k => typeof window[k] === 'function').slice(0, 20)
                                            };
                                        }
                                    """)
                                    print(f"  📄 iframe 信息: {frame_info}")
                                except:
                                    pass
                            
                            # 等待处理完成
                            print(f"  ⏳ 等待处理完成...")
                            await asyncio.sleep(3)
                            
                            # 返回列表页 - 点击"返回列表"按钮
                            try:
                                print(f"  🔍 查找返回按钮...")
                                
                                # 方法1: 优先使用精确的返回按钮选择器
                                back_btn = await spider.page.query_selector('button.comment-footer-button:has-text("返回列表")')
                                
                                if not back_btn:
                                    # 方法2: 尝试更通用的选择器
                                    back_btn = await spider.page.query_selector('.comment-footer-button')
                                
                                if not back_btn:
                                    # 方法3: 尝试其他可能的返回按钮
                                    back_btn = await spider.page.query_selector('.van-nav-bar__left, .back-btn, [class*="back"]')
                                
                                if back_btn:
                                    await back_btn.click()
                                    print(f"  ⬅️  已点击返回按钮")
                                else:
                                    # 如果没找到返回按钮，使用浏览器后退
                                    print(f"  ⚠️  未找到返回按钮，使用浏览器后退")
                                    await spider.page.go_back()
                                    print(f"  ⬅️  浏览器后退")
                                
                                # 等待返回列表页
                                print(f"  ⏳ 等待列表页加载...")
                                await asyncio.sleep(3)
                                
                                # 等待页面完全加载
                                try:
                                    await spider.page.wait_for_load_state('networkidle', timeout=10000)
                                except:
                                    pass
                                
                                # 【关键修复】重新获取模块和课程项（因为返回后 DOM 已刷新）
                                # 必须从头开始重新查询,否则旧的元素引用会失效
                                print(f"  🔄 重新查询模块列表...")
                                modules = await spider.page.query_selector_all('.van-collapse-item')
                                print(f"  📋 当前共有 {len(modules)} 个模块")
                                
                                if module_index < len(modules):
                                    # 重新获取当前模块
                                    module = modules[module_index]
                                    
                                    # 检查模块是否已展开
                                    module_class = await module.get_attribute('class')
                                    is_expanded = 'van-collapse-item--expanded' in (module_class or '')
                                    
                                    if not is_expanded:
                                        # 重新展开当前模块
                                        print(f"  🔓 重新展开模块...")
                                        title_button = await module.query_selector('.van-collapse-item__title')
                                        if title_button:
                                            await title_button.click()
                                            await asyncio.sleep(2)
                                    
                                    # 重新获取课程项列表
                                    print(f"  🔄 重新查询课程项列表...")
                                    course_items = await module.query_selector_all('.img-texts-item')
                                    print(f"  📚 当前模块共有 {len(course_items)} 个课程项")
                                
                            except Exception as e:
                                print(f"  ⚠️  返回失败: {e}")
                            
                            # 等待1分钟后继续下一个（调试模式）
                            wait_seconds = 60  # 1分钟
                            print(f"\n  ⏳ 等待 {wait_seconds} 秒后处理下一个课程...")
                            for remaining in range(wait_seconds, 0, -10):
                                print(f"  ⏰ 剩余等待时间: {remaining} 秒", end='\r')
                                await asyncio.sleep(10)
                            print()  # 换行
                            
                            completed_count += 1
                            # 不需要索引递增,下次循环会重新查找未完成的课程
                            
                        except Exception as e:
                            print(f"  ❌ 处理课程项失败: {e}")
                            import traceback
                            traceback.print_exc()
                            # 失败时等待一下再继续,避免快速重试
                            print(f"  ⏳ 等待 10 秒后继续...")
                            await asyncio.sleep(10)
                            # 继续下一次循环,重新查找未完成的课程
                            continue
                    
                    # 折叠当前模块（可选）
                    try:
                        if title_button:
                            await title_button.click()
                            await asyncio.sleep(1)
                    except:
                        pass
                    
                    # 成功处理完当前模块，移动到下一个
                    module_index += 1
                    
                except Exception as e:
                    print(f"❌ 处理模块失败: {e}")
                    import traceback
                    traceback.print_exc()
                    # 失败也移动到下一个模块，避免卡死
                    module_index += 1
                    continue
            
            print(f"\n{'='*60}")
            print(f"🎉 所有模块处理完成！共完成 {completed_count} 个课程")
            print(f"{'='*60}")
            
        except Exception as e:
            print(f"❌ 处理课程模块失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 示例3: 提取页面文本
        # try:
        #     text = await spider.page.text_content('selector')
        #     print(f"提取的文本: {text}")
        # except Exception as e:
        #     print(f"提取失败: {e}")
        
        # 示例4: 执行 JavaScript 获取数据
        # data = await spider.page.evaluate("""
        #     () => {
        #         // 在页面上下文中执行 JavaScript
        #         return document.querySelectorAll('.item').length;
        #     }
        # """)
        # print(f"数据: {data}")
        
        # 示例5: 等待网络请求完成
        # await spider.page.wait_for_load_state('networkidle')
        
        # 示例6: 导航到其他页面
        # await spider.page.goto('https://weiban.mycourse.cn/#/other-page')
        # await asyncio.sleep(2)
        
        # ========== 爬取逻辑结束 ==========
        
        # 可选：保存浏览器状态供调试
        await spider.save_state()
        
        # 保持浏览器打开，方便查看结果
        print("\n✅ 操作完成！")
        print("💡 浏览器将保持打开状态，方便你查看")
        print("按 Enter 键关闭浏览器并退出程序...")
        input()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断程序")
        
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 确保浏览器被正确关闭
        await spider.close()
        print("程序已退出")


if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())
