# coding=utf-8

import json
import os
import random
import re
import time
import webbrowser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr, formatdate, make_msgid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union

import pytz
import requests
import yaml


VERSION = "3.0.5"


# === SMTP Email Configuration ===
SMTP_CONFIGS = {
    # Gmail (using STARTTLS)
    "gmail.com": {"server": "smtp.gmail.com", "port": 587, "encryption": "TLS"},
    # QQ Mail (using SSL, more stable)
    "qq.com": {"server": "smtp.qq.com", "port": 465, "encryption": "SSL"},
    # Outlook (using STARTTLS)
    "outlook.com": {
        "server": "smtp-mail.outlook.com",
        "port": 587,
        "encryption": "TLS",
    },
    "hotmail.com": {
        "server": "smtp-mail.outlook.com",
        "port": 587,
        "encryption": "TLS",
    },
    "live.com": {"server": "smtp-mail.outlook.com", "port": 587, "encryption": "TLS"},
    # NetEase Mail (using SSL, more stable)
    "163.com": {"server": "smtp.163.com", "port": 465, "encryption": "SSL"},
    "126.com": {"server": "smtp.126.com", "port": 465, "encryption": "SSL"},
    # Sina Mail (using SSL)
    "sina.com": {"server": "smtp.sina.com", "port": 465, "encryption": "SSL"},
    # Sohu Mail (using SSL)
    "sohu.com": {"server": "smtp.sohu.com", "port": 465, "encryption": "SSL"},
}


# === Configuration Management ===
def load_config():
    """Load configuration file"""
    config_path = os.environ.get("CONFIG_PATH", "config/config.yaml")

    if not Path(config_path).exists():
        raise FileNotFoundError(f"Configuration file {config_path} does not exist")

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    print(f"Configuration file loaded successfully: {config_path}")

    # Build configuration
    config = {
        "VERSION_CHECK_URL": config_data["app"]["version_check_url"],
        "SHOW_VERSION_UPDATE": config_data["app"]["show_version_update"],
        "REQUEST_INTERVAL": config_data["crawler"]["request_interval"],
        "REPORT_MODE": os.environ.get("REPORT_MODE", "").strip()
        or config_data["report"]["mode"],
        "RANK_THRESHOLD": config_data["report"]["rank_threshold"],
        "USE_PROXY": config_data["crawler"]["use_proxy"],
        "DEFAULT_PROXY": config_data["crawler"]["default_proxy"],
        "ENABLE_CRAWLER": os.environ.get("ENABLE_CRAWLER", "").strip().lower()
        in ("true", "1")
        if os.environ.get("ENABLE_CRAWLER", "").strip()
        else config_data["crawler"]["enable_crawler"],
        "ENABLE_NOTIFICATION": os.environ.get("ENABLE_NOTIFICATION", "").strip().lower()
        in ("true", "1")
        if os.environ.get("ENABLE_NOTIFICATION", "").strip()
        else config_data["notification"]["enable_notification"],
        "MESSAGE_BATCH_SIZE": config_data["notification"]["message_batch_size"],
        "DINGTALK_BATCH_SIZE": config_data["notification"].get(
            "dingtalk_batch_size", 20000
        ),
        "FEISHU_BATCH_SIZE": config_data["notification"].get("feishu_batch_size", 29000),
        "BATCH_SEND_INTERVAL": config_data["notification"]["batch_send_interval"],
        "FEISHU_MESSAGE_SEPARATOR": config_data["notification"][
            "feishu_message_separator"
        ],
        "PUSH_WINDOW": {
            "ENABLED": os.environ.get("PUSH_WINDOW_ENABLED", "").strip().lower()
            in ("true", "1")
            if os.environ.get("PUSH_WINDOW_ENABLED", "").strip()
            else config_data["notification"]
            .get("push_window", {})
            .get("enabled", False),
            "TIME_RANGE": {
                "START": os.environ.get("PUSH_WINDOW_START", "").strip()
                or config_data["notification"]
                .get("push_window", {})
                .get("time_range", {})
                .get("start", "08:00"),
                "END": os.environ.get("PUSH_WINDOW_END", "").strip()
                or config_data["notification"]
                .get("push_window", {})
                .get("time_range", {})
                .get("end", "22:00"),
            },
            "ONCE_PER_DAY": os.environ.get("PUSH_WINDOW_ONCE_PER_DAY", "").strip().lower()
            in ("true", "1")
            if os.environ.get("PUSH_WINDOW_ONCE_PER_DAY", "").strip()
            else config_data["notification"]
            .get("push_window", {})
            .get("once_per_day", True),
            "RECORD_RETENTION_DAYS": int(
                os.environ.get("PUSH_WINDOW_RETENTION_DAYS", "").strip() or "0"
            )
            or config_data["notification"]
            .get("push_window", {})
            .get("push_record_retention_days", 7),
        },
        "WEIGHT_CONFIG": {
            "RANK_WEIGHT": config_data["weight"]["rank_weight"],
            "FREQUENCY_WEIGHT": config_data["weight"]["frequency_weight"],
            "HOTNESS_WEIGHT": config_data["weight"]["hotness_weight"],
        },
        "PLATFORMS": config_data["platforms"],
    }

    # API Keys configuration (environment variables take priority)
    api_config = config_data.get("api", {})
    config["NEWSAPI_KEY"] = os.environ.get("NEWSAPI_KEY", "").strip() or api_config.get("newsapi_key", "")
    
    # Debug: Check if NEWSAPI_KEY is loaded
    if config["NEWSAPI_KEY"]:
        print(f"✓ NEWSAPI_KEY loaded (length: {len(config['NEWSAPI_KEY'])} chars)")
    else:
        print("✗ NEWSAPI_KEY not found in environment or config file")

    # Notification channel configuration (environment variables take priority)
    notification = config_data.get("notification", {})
    webhooks = notification.get("webhooks", {})

    config["FEISHU_WEBHOOK_URL"] = os.environ.get(
        "FEISHU_WEBHOOK_URL", ""
    ).strip() or webhooks.get("feishu_url", "")
    config["DINGTALK_WEBHOOK_URL"] = os.environ.get(
        "DINGTALK_WEBHOOK_URL", ""
    ).strip() or webhooks.get("dingtalk_url", "")
    config["WEWORK_WEBHOOK_URL"] = os.environ.get(
        "WEWORK_WEBHOOK_URL", ""
    ).strip() or webhooks.get("wework_url", "")
    config["TELEGRAM_BOT_TOKEN"] = os.environ.get(
        "TELEGRAM_BOT_TOKEN", ""
    ).strip() or webhooks.get("telegram_bot_token", "")
    config["TELEGRAM_CHAT_ID"] = os.environ.get(
        "TELEGRAM_CHAT_ID", ""
    ).strip() or webhooks.get("telegram_chat_id", "")

    # Email configuration
    config["EMAIL_FROM"] = os.environ.get("EMAIL_FROM", "").strip() or webhooks.get(
        "email_from", ""
    )
    config["EMAIL_PASSWORD"] = os.environ.get(
        "EMAIL_PASSWORD", ""
    ).strip() or webhooks.get("email_password", "")
    config["EMAIL_TO"] = os.environ.get("EMAIL_TO", "").strip() or webhooks.get(
        "email_to", ""
    )
    config["EMAIL_SMTP_SERVER"] = os.environ.get(
        "EMAIL_SMTP_SERVER", ""
    ).strip() or webhooks.get("email_smtp_server", "")
    config["EMAIL_SMTP_PORT"] = os.environ.get(
        "EMAIL_SMTP_PORT", ""
    ).strip() or webhooks.get("email_smtp_port", "")

    # ntfy configuration
    config["NTFY_SERVER_URL"] = os.environ.get(
        "NTFY_SERVER_URL", "https://ntfy.sh"
    ).strip() or webhooks.get("ntfy_server_url", "https://ntfy.sh")
    config["NTFY_TOPIC"] = os.environ.get("NTFY_TOPIC", "").strip() or webhooks.get(
        "ntfy_topic", ""
    )
    config["NTFY_TOKEN"] = os.environ.get("NTFY_TOKEN", "").strip() or webhooks.get(
        "ntfy_token", ""
    )

    # Output configuration source information
    notification_sources = []
    if config["FEISHU_WEBHOOK_URL"]:
        source = "env var" if os.environ.get("FEISHU_WEBHOOK_URL") else "config file"
        notification_sources.append(f"Feishu({source})")
    if config["DINGTALK_WEBHOOK_URL"]:
        source = "env var" if os.environ.get("DINGTALK_WEBHOOK_URL") else "config file"
        notification_sources.append(f"DingTalk({source})")
    if config["WEWORK_WEBHOOK_URL"]:
        source = "env var" if os.environ.get("WEWORK_WEBHOOK_URL") else "config file"
        notification_sources.append(f"WeWork({source})")
    if config["TELEGRAM_BOT_TOKEN"] and config["TELEGRAM_CHAT_ID"]:
        token_source = (
            "env var" if os.environ.get("TELEGRAM_BOT_TOKEN") else "config file"
        )
        chat_source = "env var" if os.environ.get("TELEGRAM_CHAT_ID") else "config file"
        notification_sources.append(f"Telegram({token_source}/{chat_source})")
    if config["EMAIL_FROM"] and config["EMAIL_PASSWORD"] and config["EMAIL_TO"]:
        from_source = "env var" if os.environ.get("EMAIL_FROM") else "config file"
        notification_sources.append(f"Email({from_source})")

    if config["NTFY_SERVER_URL"] and config["NTFY_TOPIC"]:
        server_source = "env var" if os.environ.get("NTFY_SERVER_URL") else "config file"
        notification_sources.append(f"ntfy({server_source})")

    if notification_sources:
        print(f"Notification channel configuration sources: {', '.join(notification_sources)}")
    else:
        print("No notification channels configured")

    return config


print("Loading configuration...")
CONFIG = load_config()
print(f"TrendRadar v{VERSION} configuration loaded")
print(f"Number of monitored platforms: {len(CONFIG['PLATFORMS'])}")


# === Utility Functions ===
def get_utc_time():
    """Get UTC time"""
    return datetime.now(pytz.UTC)


def format_date_folder():
    """Format date folder (YYYY-MM-DD format)"""
    return get_utc_time().strftime("%Y-%m-%d")


def format_time_filename():
    """Format time filename (HH-MM format)"""
    return get_utc_time().strftime("%H-%M")


def clean_title(title: str) -> str:
    """Clean special characters from title"""
    if not isinstance(title, str):
        title = str(title)
    cleaned_title = title.replace("\n", " ").replace("\r", " ")
    cleaned_title = re.sub(r"\s+", " ", cleaned_title)
    cleaned_title = cleaned_title.strip()
    return cleaned_title


def ensure_directory_exists(directory: str):
    """Ensure directory exists"""
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_output_path(subfolder: str, filename: str) -> str:
    """Get output path"""
    date_folder = format_date_folder()
    output_dir = Path("output") / date_folder / subfolder
    ensure_directory_exists(str(output_dir))
    return str(output_dir / filename)


def check_version_update(
    current_version: str, version_url: str, proxy_url: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """Check for version updates"""
    try:
        proxies = None
        if proxy_url:
            proxies = {"http": proxy_url, "https": proxy_url}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/plain, */*",
            "Cache-Control": "no-cache",
        }

        response = requests.get(
            version_url, proxies=proxies, headers=headers, timeout=10
        )
        response.raise_for_status()

        remote_version = response.text.strip()
        print(f"Current version: {current_version}, Remote version: {remote_version}")

        # Compare versions
        def parse_version(version_str):
            try:
                parts = version_str.strip().split(".")
                if len(parts) != 3:
                    raise ValueError("Invalid version format")
                return int(parts[0]), int(parts[1]), int(parts[2])
            except:
                return 0, 0, 0

        current_tuple = parse_version(current_version)
        remote_tuple = parse_version(remote_version)

        need_update = current_tuple < remote_tuple
        return need_update, remote_version if need_update else None

    except Exception as e:
        print(f"Version check failed: {e}")
        return False, None


def is_first_crawl_today() -> bool:
    """Detect if this is the first crawl of the day"""
    date_folder = format_date_folder()
    txt_dir = Path("output") / date_folder / "txt"

    if not txt_dir.exists():
        return True

    files = sorted([f for f in txt_dir.iterdir() if f.suffix == ".txt"])
    return len(files) <= 1


def html_escape(text: str) -> str:
    """HTML escape"""
    if not isinstance(text, str):
        text = str(text)

    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


# === Push Record Management ===
class PushRecordManager:
    """Push record manager"""

    def __init__(self):
        self.record_dir = Path("output") / ".push_records"
        self.ensure_record_dir()
        self.cleanup_old_records()

    def ensure_record_dir(self):
        """Ensure record directory exists"""
        self.record_dir.mkdir(parents=True, exist_ok=True)

    def get_today_record_file(self) -> Path:
        """Get today's record file path"""
        today = get_utc_time().strftime("%Y%m%d")
        return self.record_dir / f"push_record_{today}.json"

    def cleanup_old_records(self):
        """Clean up expired push records"""
        retention_days = CONFIG["PUSH_WINDOW"]["RECORD_RETENTION_DAYS"]
        current_time = get_utc_time()

        for record_file in self.record_dir.glob("push_record_*.json"):
            try:
                date_str = record_file.stem.replace("push_record_", "")
                file_date = datetime.strptime(date_str, "%Y%m%d")
                file_date = pytz.UTC.localize(file_date)

                if (current_time - file_date).days > retention_days:
                    record_file.unlink()
                    print(f"Cleaned expired push record: {record_file.name}")
            except Exception as e:
                print(f"Failed to clean record file {record_file}: {e}")

    def has_pushed_today(self) -> bool:
        """Check if already pushed today"""
        record_file = self.get_today_record_file()

        if not record_file.exists():
            return False

        try:
            with open(record_file, "r", encoding="utf-8") as f:
                record = json.load(f)
            return record.get("pushed", False)
        except Exception as e:
            print(f"Failed to read push record: {e}")
            return False

    def has_pushed_recently(self, cooldown_hours: int = 23) -> bool:
        """Check if a push was recorded within cooldown_hours, spanning day boundaries"""
        now = get_utc_time()
        cutoff = now - timedelta(hours=cooldown_hours)

        for days_back in range(2):
            check_date = now - timedelta(days=days_back)
            date_str = check_date.strftime("%Y%m%d")
            record_file = self.record_dir / f"push_record_{date_str}.json"

            if not record_file.exists():
                continue

            try:
                with open(record_file, "r", encoding="utf-8") as f:
                    record = json.load(f)
                push_time_str = record.get("push_time", "")
                if not push_time_str:
                    continue
                push_time = datetime.strptime(push_time_str, "%Y-%m-%d %H:%M:%S")
                push_time = pytz.UTC.localize(push_time)
                if push_time >= cutoff:
                    hours_ago = (now - push_time).total_seconds() / 3600
                    print(f"Recent push detected: {push_time_str} UTC ({hours_ago:.1f}h ago)")
                    return True
            except Exception as e:
                print(f"Failed to read push record {record_file}: {e}")

        return False

    def record_push(self, report_type: str):
        """Record push"""
        record_file = self.get_today_record_file()
        now = get_utc_time()

        record = {
            "pushed": True,
            "push_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "report_type": report_type,
        }

        try:
            with open(record_file, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            print(f"Push record saved: {report_type} at {now.strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"Failed to save push record: {e}")

    def is_in_time_range(self, start_time: str, end_time: str) -> bool:
        """Check if current time is within specified time range"""
        now = get_utc_time()
        current_time = now.strftime("%H:%M")

        def normalize_time(time_str: str) -> str:
            """Normalize time string to HH:MM format"""
            try:
                parts = time_str.strip().split(":")
                if len(parts) != 2:
                    raise ValueError(f"Invalid time format: {time_str}")

                hour = int(parts[0])
                minute = int(parts[1])

                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError(f"Time out of range: {time_str}")

                return f"{hour:02d}:{minute:02d}"
            except Exception as e:
                print(f"Time formatting error '{time_str}': {e}")
                return time_str

        normalized_start = normalize_time(start_time)
        normalized_end = normalize_time(end_time)
        normalized_current = normalize_time(current_time)

        result = normalized_start <= normalized_current <= normalized_end

        if not result:
            print(f"Time window check: Current {normalized_current}, Window {normalized_start}-{normalized_end}")

        return result


class DeduplicationManager:
    """Manage deduplication state with rolling window"""

    def __init__(self, retention_hours: int = 72):
        self.retention_hours = retention_hours
        self.state_file = Path("output") / ".deduplication_state.json"
        self.state = self._load_state()
        self.current_session_new = set()

    def _load_state(self) -> Dict:
        """Load state from file"""
        if not self.state_file.exists():
            return {"history": {}}

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load deduplication state: {e}")
            return {"history": {}}

    def is_seen(self, source_id: str, title: str) -> bool:
        """Check if title has been seen"""
        # Check history
        history = self.state.get("history", {})
        if source_id in history:
            if title in history[source_id]:
                return True
        return False

    def add(self, source_id: str, title: str):
        """Add title to current session"""
        self.current_session_new.add((source_id, title))

        # Update in-memory state immediately for this session
        history = self.state.setdefault("history", {})
        source_history = history.setdefault(source_id, {})
        source_history[title] = get_utc_time().timestamp()

    def touch(self, source_id: str, title: str):
        """Update timestamp for existing title to extend its retention window"""
        history = self.state.setdefault("history", {})
        source_history = history.setdefault(source_id, {})
        source_history[title] = get_utc_time().timestamp()

    def save(self):
        """Save state to file and prune old entries"""
        now = get_utc_time().timestamp()
        retention_seconds = self.retention_hours * 3600
        cutoff_time = now - retention_seconds

        history = self.state.get("history", {})
        new_history = {}
        
        total_entries = 0
        removed_entries = 0

        for source_id, titles in history.items():
            new_titles = {}
            for title, timestamp in titles.items():
                if timestamp > cutoff_time:
                    new_titles[title] = timestamp
                    total_entries += 1
                else:
                    removed_entries += 1
            
            if new_titles:
                new_history[source_id] = new_titles

        self.state["history"] = new_history
        
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False)
            print(f"Deduplication state saved. Total entries: {total_entries}, Pruned: {removed_entries}")
        except Exception as e:
            print(f"Failed to save deduplication state: {e}")

class DataFetcher:
    """Data fetcher with multi-platform support"""

    def __init__(self, proxy_url: Optional[str] = None, newsapi_key: Optional[str] = None):
        self.proxy_url = proxy_url
        self.newsapi_key = newsapi_key

        # Initialize English platforms adapter
        try:
            from english_platforms_adapter import EnglishPlatformsAdapter
            self.english_adapter = EnglishPlatformsAdapter(
                newsapi_key=newsapi_key,
                proxy_url=proxy_url
            )
        except ImportError:
            print("Warning: English platforms adapter not found. English sources disabled.")
            self.english_adapter = None

    def fetch_data(
        self,
        id_info: Union[str, Tuple[str, str]],
        max_retries: int = 2,
        min_retry_wait: int = 3,
        max_retry_wait: int = 5,
    ) -> Tuple[Optional[str], str, str]:
        """Fetch data for specified ID with retry support"""
        if isinstance(id_info, tuple):
            id_value, alias = id_info
        else:
            id_value = id_info
            alias = id_value

        url = f"https://newsnow.busiyi.world/api/s?id={id_value}&latest"

        proxies = None
        if self.proxy_url:
            proxies = {"http": self.proxy_url, "https": self.proxy_url}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }

        retries = 0
        while retries <= max_retries:
            try:
                response = requests.get(
                    url, proxies=proxies, headers=headers, timeout=10
                )
                response.raise_for_status()

                data_text = response.text
                data_json = json.loads(data_text)

                status = data_json.get("status", "unknown")
                if status not in ["success", "cache"]:
                    raise ValueError(f"Abnormal response status: {status}")

                status_info = "latest data" if status == "success" else "cached data"
                print(f"Fetched {id_value} successfully ({status_info})")
                return data_text, id_value, alias

            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    base_wait = random.uniform(min_retry_wait, max_retry_wait)
                    additional_wait = (retries - 1) * random.uniform(1, 2)
                    wait_time = base_wait + additional_wait
                    print(f"Request for {id_value} failed: {e}. Retrying in {wait_time:.2f}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Request for {id_value} failed: {e}")
                    return None, id_value, alias
        return None, id_value, alias

    def crawl_websites(
        self,
        platforms_config: List[Dict],
        request_interval: int = CONFIG["REQUEST_INTERVAL"],
    ) -> Tuple[Dict, Dict, List]:
        """Crawl data from multiple platforms (supports both Chinese and English sources)"""
        results = {}
        id_to_name = {}
        failed_ids = []

        for i, platform in enumerate(platforms_config):
            platform_id = platform['id']
            platform_name = platform['name']
            api_type = platform.get('api', 'newsnow')  # Default to original API

            id_to_name[platform_id] = platform_name

            # Route to appropriate fetcher based on API type
            if api_type in ['reddit', 'hackernews', 'newsapi'] and self.english_adapter:
                # Use English platforms adapter
                try:
                    data = self.english_adapter.fetch(platform)
                    if data and data.get('items'):
                        results[platform_id] = {}
                        for item in data['items']:
                            title = item['title']
                            url = item.get('url', '')
                            mobile_url = item.get('mobileUrl', url)
                            rank = item.get('rank', 0)

                            if title in results[platform_id]:
                                results[platform_id][title]["ranks"].append(rank)
                            else:
                                results[platform_id][title] = {
                                    "ranks": [rank],
                                    "url": url,
                                    "mobileUrl": mobile_url
                                }
                        print(f"✓ Fetched {platform_id} successfully ({len(data['items'])} items)")
                    else:
                        error_msg = data.get('error', 'No data returned')
                        print(f"✗ {platform_id} failed: {error_msg}")
                        failed_ids.append(platform_id)
                except Exception as e:
                    print(f"✗ {platform_id} failed: {e}")
                    failed_ids.append(platform_id)

            else:
                # Use original NewNow API for Chinese platforms
                response, _, _ = self.fetch_data((platform_id, platform_name))

                if response:
                    try:
                        data = json.loads(response)
                        results[platform_id] = {}
                        for index, item in enumerate(data.get("items", []), 1):
                            title = item["title"]
                            url = item.get("url", "")
                            mobile_url = item.get("mobileUrl", "")

                            if title in results[platform_id]:
                                results[platform_id][title]["ranks"].append(index)
                            else:
                                results[platform_id][title] = {
                                    "ranks": [index],
                                    "url": url,
                                    "mobileUrl": mobile_url,
                                }
                    except json.JSONDecodeError:
                        print(f"Failed to parse {platform_id} response")
                        failed_ids.append(platform_id)
                    except Exception as e:
                        print(f"Error processing {platform_id} data: {e}")
                        failed_ids.append(platform_id)
                else:
                    failed_ids.append(platform_id)

            # Rate limiting between requests
            if i < len(platforms_config) - 1:
                actual_interval = request_interval + random.randint(-10, 20)
                actual_interval = max(50, actual_interval)
                time.sleep(actual_interval / 1000)

        print(f"Success: {list(results.keys())}, Failed: {failed_ids}")
        return results, id_to_name, failed_ids


# === Data Processing ===
def save_titles_to_file(results: Dict, id_to_name: Dict, failed_ids: List) -> str:
    """Save titles to file"""
    file_path = get_output_path("txt", f"{format_time_filename()}.txt")

    with open(file_path, "w", encoding="utf-8") as f:
        for id_value, title_data in results.items():
            # id | name or just id
            name = id_to_name.get(id_value)
            if name and name != id_value:
                f.write(f"{id_value} | {name}\n")
            else:
                f.write(f"{id_value}\n")

            # Sort titles by rank
            sorted_titles = []
            for title, info in title_data.items():
                cleaned_title = clean_title(title)
                if isinstance(info, dict):
                    ranks = info.get("ranks", [])
                    url = info.get("url", "")
                    mobile_url = info.get("mobileUrl", "")
                else:
                    ranks = info if isinstance(info, list) else []
                    url = ""
                    mobile_url = ""

                rank = ranks[0] if ranks else 1
                sorted_titles.append((rank, cleaned_title, url, mobile_url))

            sorted_titles.sort(key=lambda x: x[0])

            for rank, cleaned_title, url, mobile_url in sorted_titles:
                line = f"{rank}. {cleaned_title}"

                if url:
                    line += f" [URL:{url}]"
                if mobile_url:
                    line += f" [MOBILE:{mobile_url}]"
                f.write(line + "\n")

            f.write("\n")

        if failed_ids:
            f.write("==== Failed IDs ====\n")
            for id_value in failed_ids:
                f.write(f"{id_value}\n")

    return file_path


def load_frequency_words(
    frequency_file: Optional[str] = None,
) -> Tuple[List[Dict], List[str]]:
    """Load frequency words configuration"""
    if frequency_file is None:
        frequency_file = os.environ.get(
            "FREQUENCY_WORDS_PATH", "config/frequency_words.txt"
        )

    frequency_path = Path(frequency_file)
    if not frequency_path.exists():
        raise FileNotFoundError(f"Frequency words file {frequency_file} does not exist")

    with open(frequency_path, "r", encoding="utf-8") as f:
        content = f.read()

    word_groups = [group.strip() for group in content.split("\n\n") if group.strip()]

    processed_groups = []
    filter_words = []

    for group in word_groups:
        words = [word.strip() for word in group.split("\n") if word.strip()]

        group_required_words = []
        group_normal_words = []
        group_filter_words = []

        for word in words:
            if word.startswith("!"):
                filter_words.append(word[1:])
                group_filter_words.append(word[1:])
            elif word.startswith("+"):
                group_required_words.append(word[1:])
            else:
                group_normal_words.append(word)

        if group_required_words or group_normal_words:
            if group_normal_words:
                group_key = " ".join(group_normal_words)
            else:
                group_key = " ".join(group_required_words)

            processed_groups.append(
                {
                    "required": group_required_words,
                    "normal": group_normal_words,
                    "group_key": group_key,
                }
            )

    return processed_groups, filter_words


def parse_file_titles(file_path: Path) -> Tuple[Dict, Dict]:
    """Parse title data from a single txt file, returns (titles_by_id, id_to_name)"""
    titles_by_id = {}
    id_to_name = {}

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        sections = content.split("\n\n")

        for section in sections:
            if not section.strip() or "==== 以下ID请求Failed ====" in section:
                continue

            lines = section.strip().split("\n")
            if len(lines) < 2:
                continue

            # id | name or just id
            header_line = lines[0].strip()
            if " | " in header_line:
                parts = header_line.split(" | ", 1)
                source_id = parts[0].strip()
                name = parts[1].strip()
                id_to_name[source_id] = name
            else:
                source_id = header_line
                id_to_name[source_id] = source_id

            titles_by_id[source_id] = {}

            for line in lines[1:]:
                if line.strip():
                    try:
                        title_part = line.strip()
                        rank = None

                        # Extract rank
                        if ". " in title_part and title_part.split(". ")[0].isdigit():
                            rank_str, title_part = title_part.split(". ", 1)
                            rank = int(rank_str)

                        # Extract MOBILE URL
                        mobile_url = ""
                        if " [MOBILE:" in title_part:
                            title_part, mobile_part = title_part.rsplit(" [MOBILE:", 1)
                            if mobile_part.endswith("]"):
                                mobile_url = mobile_part[:-1]

                        # Extract URL
                        url = ""
                        if " [URL:" in title_part:
                            title_part, url_part = title_part.rsplit(" [URL:", 1)
                            if url_part.endswith("]"):
                                url = url_part[:-1]

                        title = clean_title(title_part.strip())
                        ranks = [rank] if rank is not None else [1]

                        titles_by_id[source_id][title] = {
                            "ranks": ranks,
                            "url": url,
                            "mobileUrl": mobile_url,
                        }

                    except Exception as e:
                        print(f"Error parsing title line: {line}, Error: {e}")

    return titles_by_id, id_to_name


def read_all_today_titles(
    current_platform_ids: Optional[List[str]] = None,
) -> Tuple[Dict, Dict, Dict]:
    """Read all titles from today's files, with optional filtering by current monitored platforms"""
    date_folder = format_date_folder()
    txt_dir = Path("output") / date_folder / "txt"

    if not txt_dir.exists():
        return {}, {}, {}

    all_results = {}
    final_id_to_name = {}
    title_info = {}

    files = sorted([f for f in txt_dir.iterdir() if f.suffix == ".txt"])

    for file_path in files:
        time_info = file_path.stem

        titles_by_id, file_id_to_name = parse_file_titles(file_path)

        if current_platform_ids is not None:
            filtered_titles_by_id = {}
            filtered_id_to_name = {}

            for source_id, title_data in titles_by_id.items():
                if source_id in current_platform_ids:
                    filtered_titles_by_id[source_id] = title_data
                    if source_id in file_id_to_name:
                        filtered_id_to_name[source_id] = file_id_to_name[source_id]

            titles_by_id = filtered_titles_by_id
            file_id_to_name = filtered_id_to_name

        final_id_to_name.update(file_id_to_name)

        for source_id, title_data in titles_by_id.items():
            process_source_data(
                source_id, title_data, time_info, all_results, title_info
            )

    return all_results, final_id_to_name, title_info


def process_source_data(
    source_id: str,
    title_data: Dict,
    time_info: str,
    all_results: Dict,
    title_info: Dict,
) -> None:
    """Process source data and merge duplicate titles"""
    if source_id not in all_results:
        all_results[source_id] = title_data

        if source_id not in title_info:
            title_info[source_id] = {}

        for title, data in title_data.items():
            ranks = data.get("ranks", [])
            url = data.get("url", "")
            mobile_url = data.get("mobileUrl", "")

            title_info[source_id][title] = {
                "first_time": time_info,
                "last_time": time_info,
                "count": 1,
                "ranks": ranks,
                "url": url,
                "mobileUrl": mobile_url,
            }
    else:
        for title, data in title_data.items():
            ranks = data.get("ranks", [])
            url = data.get("url", "")
            mobile_url = data.get("mobileUrl", "")

            if title not in all_results[source_id]:
                all_results[source_id][title] = {
                    "ranks": ranks,
                    "url": url,
                    "mobileUrl": mobile_url,
                }
                title_info[source_id][title] = {
                    "first_time": time_info,
                    "last_time": time_info,
                    "count": 1,
                    "ranks": ranks,
                    "url": url,
                    "mobileUrl": mobile_url,
                }
            else:
                existing_data = all_results[source_id][title]
                existing_ranks = existing_data.get("ranks", [])
                existing_url = existing_data.get("url", "")
                existing_mobile_url = existing_data.get("mobileUrl", "")

                merged_ranks = existing_ranks.copy()
                for rank in ranks:
                    if rank not in merged_ranks:
                        merged_ranks.append(rank)

                all_results[source_id][title] = {
                    "ranks": merged_ranks,
                    "url": existing_url or url,
                    "mobileUrl": existing_mobile_url or mobile_url,
                }

                title_info[source_id][title]["last_time"] = time_info
                title_info[source_id][title]["ranks"] = merged_ranks
                title_info[source_id][title]["count"] += 1
                if not title_info[source_id][title].get("url"):
                    title_info[source_id][title]["url"] = url
                if not title_info[source_id][title].get("mobileUrl"):
                    title_info[source_id][title]["mobileUrl"] = mobile_url


def detect_latest_new_titles(
    current_platform_ids: Optional[List[str]] = None,
    dedup_manager: Optional[DeduplicationManager] = None
) -> Dict:
    """Detect new titles from the latest batch using DeduplicationManager"""
    date_folder = format_date_folder()
    txt_dir = Path("output") / date_folder / "txt"

    if not txt_dir.exists():
        return {}

    files = sorted([f for f in txt_dir.iterdir() if f.suffix == ".txt"])
    if not files:
        return {}

    # Parse latest file
    latest_file = files[-1]
    latest_titles, _ = parse_file_titles(latest_file)

    # Filter latest file data if current platform list is specified
    if current_platform_ids is not None:
        filtered_latest_titles = {}
        for source_id, title_data in latest_titles.items():
            if source_id in current_platform_ids:
                filtered_latest_titles[source_id] = title_data
        latest_titles = filtered_latest_titles

    if not dedup_manager:
        # Fallback to old logic if no manager provided (shouldn't happen in new flow)
        print("Warning: No DeduplicationManager provided, falling back to daily file comparison")
        if len(files) < 2:
            return latest_titles # All are new if it's the first file and no manager
        
        # ... (Old logic omitted for brevity, but could be kept as fallback)
        # For now, let's just return empty if no manager and >1 file to be safe, 
        # or implement a simple fallback. 
        # Given the instruction is to REPLACE, we will assume manager is always passed.
        return {}

    new_titles = {}

    for source_id, source_titles in latest_titles.items():
        source_new_titles = {}
        for title, title_data in source_titles.items():
            is_new = not dedup_manager.is_seen(source_id, title)

            if is_new:
                # New title - add to dedup state and mark as new
                dedup_manager.add(source_id, title)
                source_new_titles[title] = title_data
            else:
                # Seen before - just refresh timestamp to extend retention window
                dedup_manager.touch(source_id, title)

        if source_new_titles:
            new_titles[source_id] = source_new_titles

    return new_titles


# === Statistics and Analysis ===
def calculate_news_weight(
    title_data: Dict, rank_threshold: int = CONFIG["RANK_THRESHOLD"]
) -> float:
    """Calculate news weight for sorting"""
    ranks = title_data.get("ranks", [])
    if not ranks:
        return 0.0

    count = title_data.get("count", len(ranks))
    weight_config = CONFIG["WEIGHT_CONFIG"]

    # Rank weight: Σ(11 - min(rank, 10)) / appearance count
    rank_scores = []
    for rank in ranks:
        score = 11 - min(rank, 10)
        rank_scores.append(score)

    rank_weight = sum(rank_scores) / len(ranks) if ranks else 0

    # Frequency weight: min(appearance count, 10) × 10
    frequency_weight = min(count, 10) * 10

    # Hotness bonus: high rank count / total appearance count × 100
    high_rank_count = sum(1 for rank in ranks if rank <= rank_threshold)
    hotness_ratio = high_rank_count / len(ranks) if ranks else 0
    hotness_weight = hotness_ratio * 100

    total_weight = (
        rank_weight * weight_config["RANK_WEIGHT"]
        + frequency_weight * weight_config["FREQUENCY_WEIGHT"]
        + hotness_weight * weight_config["HOTNESS_WEIGHT"]
    )

    return total_weight


def matches_word_groups(
    title: str, word_groups: List[Dict], filter_words: List[str]
) -> bool:
    """Check if title matches word group rules"""
    # If no word groups configured, match all titles (support displaying all news)
    if not word_groups:
        return True

    title_lower = title.lower()

    # Filter word check
    if any(filter_word.lower() in title_lower for filter_word in filter_words):
        return False

    # Word group matching check
    for group in word_groups:
        required_words = group["required"]
        normal_words = group["normal"]

        # Required word check
        if required_words:
            all_required_present = all(
                req_word.lower() in title_lower for req_word in required_words
            )
            if not all_required_present:
                continue

        # Normal word check
        if normal_words:
            any_normal_present = any(
                normal_word.lower() in title_lower for normal_word in normal_words
            )
            if not any_normal_present:
                continue

        return True

    return False


def format_time_display(first_time: str, last_time: str) -> str:
    """Format time display"""
    if not first_time:
        return ""
    if first_time == last_time or not last_time:
        return first_time
    else:
        return f"[{first_time} ~ {last_time}]"


def format_rank_display(ranks: List[int], rank_threshold: int, format_type: str) -> str:
    """Unified rank formatting method"""
    if not ranks:
        return ""

    unique_ranks = sorted(set(ranks))
    min_rank = unique_ranks[0]
    max_rank = unique_ranks[-1]

    if format_type == "html":
        highlight_start = "<font color='red'><strong>"
        highlight_end = "</strong></font>"
    elif format_type == "feishu":
        highlight_start = "<font color='red'>**"
        highlight_end = "**</font>"
    elif format_type == "dingtalk":
        highlight_start = "**"
        highlight_end = "**"
    elif format_type == "wework":
        highlight_start = "**"
        highlight_end = "**"
    elif format_type == "telegram":
        highlight_start = "<b>"
        highlight_end = "</b>"
    else:
        highlight_start = "**"
        highlight_end = "**"

    if min_rank <= rank_threshold:
        if min_rank == max_rank:
            return f"{highlight_start}[{min_rank}]{highlight_end}"
        else:
            return f"{highlight_start}[{min_rank} - {max_rank}]{highlight_end}"
    else:
        if min_rank == max_rank:
            return f"[{min_rank}]"
        else:
            return f"[{min_rank} - {max_rank}]"


def count_word_frequency(
    results: Dict,
    word_groups: List[Dict],
    filter_words: List[str],
    id_to_name: Dict,
    title_info: Optional[Dict] = None,
    rank_threshold: int = CONFIG["RANK_THRESHOLD"],
    new_titles: Optional[Dict] = None,
    mode: str = "daily",
) -> Tuple[List[Dict], int]:
    """Count word frequency, supporting required words, frequency words, filter words, and marking new titles"""

    # If no word groups configured, create a virtual group containing all news
    if not word_groups:
        print("Frequency words configuration is empty, will display all news")
        word_groups = [{"required": [], "normal": [], "group_key": "All News"}]
        filter_words = []  # Clear filter words, display all news

    is_first_today = is_first_crawl_today()

    # Determine data source to process and new marking logic
    if mode == "incremental":
        if is_first_today:
            # Incremental mode + first crawl of the day: process all news, mark all as new
            results_to_process = results
            all_news_are_new = True
        else:
            # Incremental mode + not first crawl: only process new news
            results_to_process = new_titles if new_titles else {}
            all_news_are_new = True
    elif mode == "current":
        # Current mode: only process current batch news, but statistics come from all history
        if title_info:
            latest_time = None
            for source_titles in title_info.values():
                for title_data in source_titles.values():
                    last_time = title_data.get("last_time", "")
                    if last_time:
                        if latest_time is None or last_time > latest_time:
                            latest_time = last_time

            # Only process news where last_time equals latest time
            if latest_time:
                results_to_process = {}
                for source_id, source_titles in results.items():
                    if source_id in title_info:
                        filtered_titles = {}
                        for title, title_data in source_titles.items():
                            if title in title_info[source_id]:
                                info = title_info[source_id][title]
                                if info.get("last_time") == latest_time:
                                    filtered_titles[title] = title_data
                        if filtered_titles:
                            results_to_process[source_id] = filtered_titles

                print(
                    f"Current ranking mode: Latest time {latest_time}, filtered {sum(len(titles) for titles in results_to_process.values())} current ranking news"
                )
            else:
                results_to_process = results
        else:
            results_to_process = results
        all_news_are_new = False
    else:
        # Daily summary mode: process all news
        results_to_process = results
        all_news_are_new = False
        total_input_news = sum(len(titles) for titles in results.values())
        filter_status = (
            "show all"
            if len(word_groups) == 1 and word_groups[0]["group_key"] == "All News"
            else "frequency word filtering"
        )
        print(f"Daily summary mode: Processing {total_input_news} news items, mode: {filter_status}")

    word_stats = {}
    total_titles = 0
    processed_titles = {}
    matched_new_count = 0

    if title_info is None:
        title_info = {}
    if new_titles is None:
        new_titles = {}

    for group in word_groups:
        group_key = group["group_key"]
        word_stats[group_key] = {"count": 0, "titles": {}}

    for source_id, titles_data in results_to_process.items():
        total_titles += len(titles_data)

        if source_id not in processed_titles:
            processed_titles[source_id] = {}

        for title, title_data in titles_data.items():
            if title in processed_titles.get(source_id, {}):
                continue

            # Use unified matching logic
            matches_frequency_words = matches_word_groups(
                title, word_groups, filter_words
            )

            if not matches_frequency_words:
                continue

            # If incremental mode or current mode first batch, count matched new news
            if (mode == "incremental" and all_news_are_new) or (
                mode == "current" and is_first_today
            ):
                matched_new_count += 1

            source_ranks = title_data.get("ranks", [])
            source_url = title_data.get("url", "")
            source_mobile_url = title_data.get("mobileUrl", "")

            # Find matching word group
            title_lower = title.lower()
            for group in word_groups:
                required_words = group["required"]
                normal_words = group["normal"]

                # If "All News" mode, all titles match the single (only) word group
                if len(word_groups) == 1 and word_groups[0]["group_key"] == "All News":
                    group_key = group["group_key"]
                    word_stats[group_key]["count"] += 1
                    if source_id not in word_stats[group_key]["titles"]:
                        word_stats[group_key]["titles"][source_id] = []
                else:
                    # Original matching logic
                    if required_words:
                        all_required_present = all(
                            req_word.lower() in title_lower
                            for req_word in required_words
                        )
                        if not all_required_present:
                            continue

                    if normal_words:
                        any_normal_present = any(
                            normal_word.lower() in title_lower
                            for normal_word in normal_words
                        )
                        if not any_normal_present:
                            continue

                    group_key = group["group_key"]
                    word_stats[group_key]["count"] += 1
                    if source_id not in word_stats[group_key]["titles"]:
                        word_stats[group_key]["titles"][source_id] = []

                first_time = ""
                last_time = ""
                count_info = 1
                ranks = source_ranks if source_ranks else []
                url = source_url
                mobile_url = source_mobile_url

                # For current mode, get complete data from historical statistics
                if (
                    mode == "current"
                    and title_info
                    and source_id in title_info
                    and title in title_info[source_id]
                ):
                    info = title_info[source_id][title]
                    first_time = info.get("first_time", "")
                    last_time = info.get("last_time", "")
                    count_info = info.get("count", 1)
                    if "ranks" in info and info["ranks"]:
                        ranks = info["ranks"]
                    url = info.get("url", source_url)
                    mobile_url = info.get("mobileUrl", source_mobile_url)
                elif (
                    title_info
                    and source_id in title_info
                    and title in title_info[source_id]
                ):
                    info = title_info[source_id][title]
                    first_time = info.get("first_time", "")
                    last_time = info.get("last_time", "")
                    count_info = info.get("count", 1)
                    if "ranks" in info and info["ranks"]:
                        ranks = info["ranks"]
                    url = info.get("url", source_url)
                    mobile_url = info.get("mobileUrl", source_mobile_url)

                if not ranks:
                    ranks = [99]

                time_display = format_time_display(first_time, last_time)

                source_name = id_to_name.get(source_id, source_id)

                # Check if this is new
                is_new = False
                if all_news_are_new:
                    # In incremental mode, all processed news are new, or all news in first batch of the day are new
                    is_new = True
                elif new_titles and source_id in new_titles:
                    # Check if in new titles list
                    new_titles_for_source = new_titles[source_id]
                    is_new = title in new_titles_for_source

                word_stats[group_key]["titles"][source_id].append(
                    {
                        "title": title,
                        "source_name": source_name,
                        "first_time": first_time,
                        "last_time": last_time,
                        "time_display": time_display,
                        "count": count_info,
                        "ranks": ranks,
                        "rank_threshold": rank_threshold,
                        "url": url,
                        "mobileUrl": mobile_url,
                        "is_new": is_new,
                    }
                )

                if source_id not in processed_titles:
                    processed_titles[source_id] = {}
                processed_titles[source_id][title] = True

                break

    # Print summary information at the end
    if mode == "incremental":
        if is_first_today:
            total_input_news = sum(len(titles) for titles in results.values())
            filter_status = (
                "show all"
                if len(word_groups) == 1 and word_groups[0]["group_key"] == "All News"
                else "match frequency words"
            )
            print(
                f"Incremental mode: First crawl of the day, {matched_new_count} out of {total_input_news} news {filter_status}"
            )
        else:
            if new_titles:
                total_new_count = sum(len(titles) for titles in new_titles.values())
                filter_status = (
                    "show all"
                    if len(word_groups) == 1
                    and word_groups[0]["group_key"] == "All News"
                    else "match frequency words"
                )
                print(
                    f"Incremental mode: {matched_new_count} out of {total_new_count} new news {filter_status}"
                )
                if matched_new_count == 0 and len(word_groups) > 1:
                    print("Incremental mode: No new news matches frequency words, notification will not be sent")
            else:
                print("Incremental mode: No new news detected")
    elif mode == "current":
        total_input_news = sum(len(titles) for titles in results_to_process.values())
        if is_first_today:
            filter_status = (
                "show all"
                if len(word_groups) == 1 and word_groups[0]["group_key"] == "All News"
                else "match frequency words"
            )
            print(
                f"Current ranking mode: First crawl of the day, {matched_new_count} out of {total_input_news} current ranking news {filter_status}"
            )
        else:
            matched_count = sum(stat["count"] for stat in word_stats.values())
            filter_status = (
                "show all"
                if len(word_groups) == 1 and word_groups[0]["group_key"] == "All News"
                else "match frequency words"
            )
            print(
                f"Current ranking mode: {matched_count} out of {total_input_news} current ranking news {filter_status}"
            )

    stats = []
    for group_key, data in word_stats.items():
        all_titles = []
        for source_id, title_list in data["titles"].items():
            all_titles.extend(title_list)

        # Sort by weight
        sorted_titles = sorted(
            all_titles,
            key=lambda x: (
                -calculate_news_weight(x, rank_threshold),
                min(x["ranks"]) if x["ranks"] else 999,
                -x["count"],
            ),
        )

        stats.append(
            {
                "word": group_key,
                "count": data["count"],
                "titles": sorted_titles,
                "percentage": (
                    round(data["count"] / total_titles * 100, 2)
                    if total_titles > 0
                    else 0
                ),
            }
        )

    stats.sort(key=lambda x: x["count"], reverse=True)
    return stats, total_titles


# === Report Generation ===
def prepare_report_data(
    stats: List[Dict],
    failed_ids: Optional[List] = None,
    new_titles: Optional[Dict] = None,
    id_to_name: Optional[Dict] = None,
    mode: str = "daily",
) -> Dict:
    """Prepare report data"""
    processed_new_titles = []

    # Hide new news section in incremental mode
    hide_new_section = mode == "incremental"

    # Only process new news section if not hidden
    if not hide_new_section:
        filtered_new_titles = {}
        if new_titles and id_to_name:
            word_groups, filter_words = load_frequency_words()
            for source_id, titles_data in new_titles.items():
                filtered_titles = {}
                for title, title_data in titles_data.items():
                    if matches_word_groups(title, word_groups, filter_words):
                        filtered_titles[title] = title_data
                if filtered_titles:
                    filtered_new_titles[source_id] = filtered_titles

        if filtered_new_titles and id_to_name:
            for source_id, titles_data in filtered_new_titles.items():
                source_name = id_to_name.get(source_id, source_id)
                source_titles = []

                for title, title_data in titles_data.items():
                    url = title_data.get("url", "")
                    mobile_url = title_data.get("mobileUrl", "")
                    ranks = title_data.get("ranks", [])

                    processed_title = {
                        "title": title,
                        "source_name": source_name,
                        "time_display": "",
                        "count": 1,
                        "ranks": ranks,
                        "rank_threshold": CONFIG["RANK_THRESHOLD"],
                        "url": url,
                        "mobile_url": mobile_url,
                        "is_new": True,
                    }
                    source_titles.append(processed_title)

                if source_titles:
                    processed_new_titles.append(
                        {
                            "source_id": source_id,
                            "source_name": source_name,
                            "titles": source_titles,
                        }
                    )

    processed_stats = []
    for stat in stats:
        if stat["count"] <= 0:
            continue

        processed_titles = []
        for title_data in stat["titles"]:
            processed_title = {
                "title": title_data["title"],
                "source_name": title_data["source_name"],
                "time_display": title_data["time_display"],
                "count": title_data["count"],
                "ranks": title_data["ranks"],
                "rank_threshold": title_data["rank_threshold"],
                "url": title_data.get("url", ""),
                "mobile_url": title_data.get("mobileUrl", ""),
                "is_new": title_data.get("is_new", False),
            }
            processed_titles.append(processed_title)

        processed_stats.append(
            {
                "word": stat["word"],
                "count": stat["count"],
                "percentage": stat.get("percentage", 0),
                "titles": processed_titles,
            }
        )

    return {
        "stats": processed_stats,
        "new_titles": processed_new_titles,
        "failed_ids": failed_ids or [],
        "total_new_count": sum(
            len(source["titles"]) for source in processed_new_titles
        ),
    }


def format_title_for_platform(
    platform: str, title_data: Dict, show_source: bool = True
) -> str:
    """统一的Title格式化方法"""
    rank_display = format_rank_display(
        title_data["ranks"], title_data["rank_threshold"], platform
    )

    link_url = title_data["mobile_url"] or title_data["url"]

    cleaned_title = clean_title(title_data["title"])

    if platform == "feishu":
        if link_url:
            formatted_title = f"[{cleaned_title}]({link_url})"
        else:
            formatted_title = cleaned_title

        title_prefix = "🆕 " if title_data.get("is_new") else ""

        if show_source:
            result = f"<font color='grey'>[{title_data['source_name']}]</font> {title_prefix}{formatted_title}"
        else:
            result = f"{title_prefix}{formatted_title}"

        if rank_display:
            result += f" {rank_display}"
        if title_data["time_display"]:
            result += f" <font color='grey'>- {title_data['time_display']}</font>"
        if title_data["count"] > 1:
            result += f" <font color='green'>({title_data['count']}times)</font>"

        return result

    elif platform == "dingtalk":
        if link_url:
            formatted_title = f"[{cleaned_title}]({link_url})"
        else:
            formatted_title = cleaned_title

        title_prefix = "🆕 " if title_data.get("is_new") else ""

        if show_source:
            result = f"[{title_data['source_name']}] {title_prefix}{formatted_title}"
        else:
            result = f"{title_prefix}{formatted_title}"

        if rank_display:
            result += f" {rank_display}"
        if title_data["time_display"]:
            result += f" - {title_data['time_display']}"
        if title_data["count"] > 1:
            result += f" ({title_data['count']}times)"

        return result

    elif platform == "wework":
        if link_url:
            formatted_title = f"[{cleaned_title}]({link_url})"
        else:
            formatted_title = cleaned_title

        title_prefix = "🆕 " if title_data.get("is_new") else ""

        if show_source:
            result = f"[{title_data['source_name']}] {title_prefix}{formatted_title}"
        else:
            result = f"{title_prefix}{formatted_title}"

        if rank_display:
            result += f" {rank_display}"
        if title_data["time_display"]:
            result += f" - {title_data['time_display']}"
        if title_data["count"] > 1:
            result += f" ({title_data['count']}times)"

        return result

    elif platform == "telegram":
        if link_url:
            formatted_title = f'<a href="{link_url}">{html_escape(cleaned_title)}</a>'
        else:
            formatted_title = cleaned_title

        title_prefix = "🆕 " if title_data.get("is_new") else ""

        if show_source:
            result = f"[{title_data['source_name']}] {title_prefix}{formatted_title}"
        else:
            result = f"{title_prefix}{formatted_title}"

        if rank_display:
            result += f" {rank_display}"
        if title_data["time_display"]:
            result += f" <code>- {title_data['time_display']}</code>"
        if title_data["count"] > 1:
            result += f" <code>({title_data['count']}times)</code>"

        return result

    elif platform == "ntfy":
        if link_url:
            formatted_title = f"[{cleaned_title}]({link_url})"
        else:
            formatted_title = cleaned_title

        title_prefix = "🆕 " if title_data.get("is_new") else ""

        if show_source:
            result = f"[{title_data['source_name']}] {title_prefix}{formatted_title}"
        else:
            result = f"{title_prefix}{formatted_title}"

        if rank_display:
            result += f" {rank_display}"
        if title_data["time_display"]:
            result += f" `- {title_data['time_display']}`"
        if title_data["count"] > 1:
            result += f" `({title_data['count']}times)`"

        return result

    elif platform == "html":
        rank_display = format_rank_display(
            title_data["ranks"], title_data["rank_threshold"], "html"
        )

        link_url = title_data["mobile_url"] or title_data["url"]

        escaped_title = html_escape(cleaned_title)
        escaped_source_name = html_escape(title_data["source_name"])

        if link_url:
            escaped_url = html_escape(link_url)
            formatted_title = f'[{escaped_source_name}] <a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
        else:
            formatted_title = (
                f'[{escaped_source_name}] <span class="no-link">{escaped_title}</span>'
            )

        if rank_display:
            formatted_title += f" {rank_display}"
        if title_data["time_display"]:
            escaped_time = html_escape(title_data["time_display"])
            formatted_title += f" <font color='grey'>- {escaped_time}</font>"
        if title_data["count"] > 1:
            formatted_title += f" <font color='green'>({title_data['count']}times)</font>"

        if title_data.get("is_new"):
            formatted_title = f"<div class='new-title'>🆕 {formatted_title}</div>"

        return formatted_title

    else:
        return cleaned_title


def generate_html_report(
    stats: List[Dict],
    total_titles: int,
    failed_ids: Optional[List] = None,
    new_titles: Optional[Dict] = None,
    id_to_name: Optional[Dict] = None,
    mode: str = "daily",
    is_daily_summary: bool = False,
    update_info: Optional[Dict] = None,
) -> str:
    """Generate HTML report"""
    if is_daily_summary:
        if mode == "current":
            filename = "Current Ranking Summary.html"
        elif mode == "incremental":
            filename = "Incremental Summary.html"
        else:
            filename = "Daily Summary.html"
    else:
        filename = f"{format_time_filename()}.html"

    file_path = get_output_path("html", filename)

    report_data = prepare_report_data(stats, failed_ids, new_titles, id_to_name, mode)

    html_content = render_html_content(
        report_data, total_titles, is_daily_summary, mode, update_info
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    if is_daily_summary:
        root_file_path = Path("index.html")
        with open(root_file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    return file_path


def render_html_content(
    report_data: Dict,
    total_titles: int,
    is_daily_summary: bool = False,
    mode: str = "daily",
    update_info: Optional[Dict] = None,
) -> str:
    """Render HTML content"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TrendRadar - AI, Finance & Technology News</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js" integrity="sha512-BNaRQnYJYiPSqHHDb58B0yaPfCu+Wgds8Gp/gU33kqBtgNS4tSPHuGibyoeqMV/TJlSKda6FXzoEyYGjTe+vXA==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <style>
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #1a202c;
                line-height: 1.6;
                -webkit-font-smoothing: antialiased;
            }

            .container {
                max-width: 680px;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            }

            .header {
                background: linear-gradient(135deg, #1e3a8a 0%, #5b21b6 50%, #7e22ce 100%);
                color: white;
                padding: 40px 32px;
                text-align: center;
                position: relative;
                border-bottom: 4px solid #fbbf24;
            }

            .header::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899, #f59e0b);
            }
            
            .save-buttons {
                position: absolute;
                top: 16px;
                right: 16px;
                display: flex;
                gap: 8px;
            }
            
            .save-btn {
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 500;
                transition: all 0.2s ease;
                backdrop-filter: blur(10px);
                white-space: nowrap;
            }
            
            .save-btn:hover {
                background: rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.5);
                transform: translateY(-1px);
            }
            
            .save-btn:active {
                transform: translateY(0);
            }
            
            .save-btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            
            .logo {
                font-size: 48px;
                margin-bottom: 12px;
                filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
            }

            .header-title {
                font-size: 32px;
                font-weight: 800;
                margin: 0 0 8px 0;
                letter-spacing: -1px;
                text-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }

            .header-subtitle {
                font-size: 15px;
                opacity: 0.95;
                margin: 0 0 28px 0;
                font-weight: 400;
                letter-spacing: 0.3px;
            }

            .stats-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 12px;
                margin-top: 24px;
            }

            .stat-card {
                background: rgba(255, 255, 255, 0.15);
                backdrop-filter: blur(10px);
                border-radius: 12px;
                padding: 16px 12px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                transition: transform 0.2s ease, background 0.2s ease;
            }

            .stat-card:hover {
                transform: translateY(-2px);
                background: rgba(255, 255, 255, 0.2);
            }

            .stat-label {
                display: block;
                font-size: 11px;
                opacity: 0.85;
                margin-bottom: 6px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                font-weight: 600;
            }

            .stat-value {
                font-weight: 700;
                font-size: 20px;
                line-height: 1;
                text-shadow: 0 1px 2px rgba(0,0,0,0.1);
            }
            
            .content {
                padding: 32px 28px;
                background: #fafbfc;
            }

            .word-group {
                margin-bottom: 36px;
                background: white;
                border-radius: 12px;
                padding: 24px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                border: 1px solid #e5e7eb;
            }

            .word-group:first-child {
                margin-top: 0;
            }

            .word-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 20px;
                padding-bottom: 12px;
                border-bottom: 2px solid #f3f4f6;
            }

            .word-info {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .word-name {
                font-size: 20px;
                font-weight: 700;
                color: #111827;
                letter-spacing: -0.3px;
            }

            .word-count {
                background: #f3f4f6;
                color: #6b7280;
                font-size: 12px;
                font-weight: 600;
                padding: 4px 12px;
                border-radius: 12px;
            }

            .word-count.hot {
                background: #fee2e2;
                color: #dc2626;
                font-weight: 700;
            }

            .word-count.warm {
                background: #ffedd5;
                color: #ea580c;
                font-weight: 700;
            }
            
            .word-index {
                background: #f9fafb;
                color: #9ca3af;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 8px;
            }

            .news-item {
                margin-bottom: 16px;
                padding: 18px;
                background: #fafbfc;
                border-radius: 10px;
                position: relative;
                display: flex;
                gap: 14px;
                align-items: flex-start;
                border: 1px solid #f3f4f6;
                transition: all 0.2s ease;
            }

            .news-item:hover {
                background: #f9fafb;
                border-color: #e5e7eb;
                box-shadow: 0 2px 4px rgba(0,0,0,0.04);
            }

            .news-item:last-child {
                margin-bottom: 0;
            }

            .news-item.new {
                border-left: 3px solid #fbbf24;
                background: #fffbeb;
            }

            .news-item.new::after {
                content: "NEW";
                position: absolute;
                top: 16px;
                right: 16px;
                background: #fbbf24;
                color: #92400e;
                font-size: 9px;
                font-weight: 800;
                padding: 4px 8px;
                border-radius: 6px;
                letter-spacing: 0.5px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            }
            
            .news-number {
                color: #6b7280;
                font-size: 14px;
                font-weight: 700;
                min-width: 28px;
                text-align: center;
                flex-shrink: 0;
                background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
                border-radius: 8px;
                width: 28px;
                height: 28px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-top: 2px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            }

            .news-content {
                flex: 1;
                min-width: 0;
                padding-right: 50px;
            }

            .news-item.new .news-content {
                padding-right: 60px;
            }

            .news-header {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 10px;
                flex-wrap: wrap;
            }

            .source-name {
                color: #6b7280;
                font-size: 12px;
                font-weight: 600;
                background: #f3f4f6;
                padding: 3px 10px;
                border-radius: 6px;
            }

            .rank-num {
                color: #fff;
                background: #6b7280;
                font-size: 10px;
                font-weight: 800;
                padding: 3px 8px;
                border-radius: 6px;
                min-width: 22px;
                text-align: center;
                box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            }

            .rank-num.top {
                background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
            }

            .rank-num.high {
                background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%);
            }
            
            .time-info {
                color: #999;
                font-size: 11px;
            }
            
            .count-info {
                color: #059669;
                font-size: 11px;
                font-weight: 500;
            }

            .category-tag {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 10px;
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.3px;
            }

            .category-ai {
                background: #dbeafe;
                color: #1e40af;
            }

            .category-finance {
                background: #d1fae5;
                color: #065f46;
            }

            .category-tech {
                background: #fce7f3;
                color: #9f1239;
            }

            .category-crypto {
                background: #fef3c7;
                color: #92400e;
            }
            
            .news-title {
                font-size: 15px;
                line-height: 1.5;
                color: #111827;
                margin: 0;
                font-weight: 500;
            }

            .news-link {
                color: #2563eb;
                text-decoration: none;
                transition: color 0.2s ease;
                font-weight: 500;
            }

            .news-link:hover {
                color: #1d4ed8;
                text-decoration: underline;
            }

            .news-link:visited {
                color: #7c3aed;
            }
            
            .new-section {
                margin-top: 40px;
                padding-top: 24px;
                border-top: 2px solid #f0f0f0;
            }
            
            .new-section-title {
                color: #1a1a1a;
                font-size: 16px;
                font-weight: 600;
                margin: 0 0 20px 0;
            }
            
            .new-source-group {
                margin-bottom: 24px;
            }
            
            .new-source-title {
                color: #666;
                font-size: 13px;
                font-weight: 500;
                margin: 0 0 12px 0;
                padding-bottom: 6px;
                border-bottom: 1px solid #f5f5f5;
            }
            
            .new-item {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 8px 0;
                border-bottom: 1px solid #f9f9f9;
            }
            
            .new-item:last-child {
                border-bottom: none;
            }
            
            .new-item-number {
                color: #999;
                font-size: 12px;
                font-weight: 600;
                min-width: 18px;
                text-align: center;
                flex-shrink: 0;
                background: #f8f9fa;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .new-item-rank {
                color: #fff;
                background: #6b7280;
                font-size: 10px;
                font-weight: 700;
                padding: 3px 6px;
                border-radius: 8px;
                min-width: 20px;
                text-align: center;
                flex-shrink: 0;
            }
            
            .new-item-rank.top { background: #dc2626; }
            .new-item-rank.high { background: #ea580c; }
            
            .new-item-content {
                flex: 1;
                min-width: 0;
            }
            
            .new-item-title {
                font-size: 14px;
                line-height: 1.4;
                color: #1a1a1a;
                margin: 0;
            }
            
            .error-section {
                background: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 24px;
            }
            
            .error-title {
                color: #dc2626;
                font-size: 14px;
                font-weight: 600;
                margin: 0 0 8px 0;
            }
            
            .error-list {
                list-style: none;
                padding: 0;
                margin: 0;
            }
            
            .error-item {
                color: #991b1b;
                font-size: 13px;
                padding: 2px 0;
                font-family: 'SF Mono', Consolas, monospace;
            }
            
            .footer {
                background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
                color: white;
                padding: 28px 32px;
                text-align: center;
                border-top: 3px solid #fbbf24;
            }

            .footer-content {
                font-size: 13px;
                line-height: 1.8;
                opacity: 0.9;
            }

            .footer-link {
                color: #fbbf24;
                text-decoration: none;
                font-weight: 600;
                transition: all 0.2s ease;
            }

            .footer-link:hover {
                color: #fcd34d;
                text-decoration: underline;
            }

            .project-name {
                font-weight: 700;
                color: white;
                font-size: 14px;
            }

            .footer-tagline {
                margin-top: 8px;
                font-size: 12px;
                opacity: 0.7;
            }
            
            @media (max-width: 680px) {
                body { padding: 12px; }
                .container { border-radius: 12px; }
                .header { padding: 32px 24px; }
                .content { padding: 24px 20px; }
                .footer { padding: 24px 20px; }
                .logo { font-size: 40px; }
                .header-title { font-size: 26px; }
                .header-subtitle { font-size: 14px; }
                .stats-grid { grid-template-columns: 1fr 1fr; gap: 10px; }
                .stat-card { padding: 14px 10px; }
                .stat-value { font-size: 18px; }
                .word-group { padding: 20px; margin-bottom: 24px; }
                .word-name { font-size: 18px; }
                .news-item { padding: 14px; gap: 10px; }
                .news-header { gap: 6px; }
                .news-content { padding-right: 45px; }
                .news-number { width: 24px; height: 24px; font-size: 12px; }
                .new-item { gap: 8px; }
                .save-buttons {
                    position: static;
                    margin-bottom: 16px;
                    display: flex;
                    gap: 8px;
                    justify-content: center;
                    flex-direction: column;
                    width: 100%;
                }
                .save-btn { width: 100%; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="save-buttons">
                    <button class="save-btn" onclick="saveAsImage()">Save as Image</button>
                    <button class="save-btn" onclick="saveAsMultipleImages()">Save in Segments</button>
                </div>
                <div class="logo">📊</div>
                <div class="header-title">TrendRadar</div>
                <div class="header-subtitle">AI, Finance & Technology News Analysis</div>
                <div class="stats-grid">
                    <div class="stat-card">
                        <span class="stat-label">Mode</span>
                        <span class="stat-value">"""

    # Process report type display
    if is_daily_summary:
        if mode == "current":
            html += "Current"
        elif mode == "incremental":
            html += "Delta"
        else:
            html += "Daily"
    else:
        html += "Live"

    html += """</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">Total</span>
                        <span class="stat-value">"""

    html += str(total_titles)

    # Calculate filtered trending news count
    hot_news_count = sum(len(stat["titles"]) for stat in report_data["stats"])

    html += """</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">Trending</span>
                        <span class="stat-value">"""

    html += str(hot_news_count)

    html += """</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">Time</span>
                        <span class="stat-value">"""

    now = get_utc_time()
    html += now.strftime("%H:%M")

    html += """</span>
                    </div>
                </div>
            </div>
            
            <div class="content">"""

    # Process failed ID error information
    if report_data["failed_ids"]:
        html += """
                <div class="error-section">
                    <div class="error-title">⚠️ Failed Platforms</div>
                    <ul class="error-list">"""
        for id_value in report_data["failed_ids"]:
            html += f'<li class="error-item">{html_escape(id_value)}</li>'
        html += """
                    </ul>
                </div>"""

    # Process main statistical data
    if report_data["stats"]:
        total_count = len(report_data["stats"])

        for i, stat in enumerate(report_data["stats"], 1):
            count = stat["count"]

            # Determine hotness level
            if count >= 10:
                count_class = "hot"
            elif count >= 5:
                count_class = "warm"
            else:
                count_class = ""

            escaped_word = html_escape(stat["word"])

            html += f"""
                <div class="word-group">
                    <div class="word-header">
                        <div class="word-info">
                            <div class="word-name">{escaped_word}</div>
                            <div class="word-count {count_class}">{count} items</div>
                        </div>
                        <div class="word-index">{i}/{total_count}</div>
                    </div>"""

            # Process news titles under each word group, numbering each news item
            for j, title_data in enumerate(stat["titles"], 1):
                is_new = title_data.get("is_new", False)
                new_class = "new" if is_new else ""

                html += f"""
                    <div class="news-item {new_class}">
                        <div class="news-number">{j}</div>
                        <div class="news-content">
                            <div class="news-header">
                                <span class="source-name">{html_escape(title_data["source_name"])}</span>"""

                # Process rank display
                ranks = title_data.get("ranks", [])
                if ranks:
                    min_rank = min(ranks)
                    max_rank = max(ranks)
                    rank_threshold = title_data.get("rank_threshold", 10)

                    # Determine rank level
                    if min_rank <= 3:
                        rank_class = "top"
                    elif min_rank <= rank_threshold:
                        rank_class = "high"
                    else:
                        rank_class = ""

                    if min_rank == max_rank:
                        rank_text = str(min_rank)
                    else:
                        rank_text = f"{min_rank}-{max_rank}"

                    html += f'<span class="rank-num {rank_class}">{rank_text}</span>'

                # Process time display
                time_display = title_data.get("time_display", "")
                if time_display:
                    # Simplify time display format, replace tilde with ~
                    simplified_time = (
                        time_display.replace(" ~ ", "~")
                        .replace("[", "")
                        .replace("]", "")
                    )
                    html += (
                        f'<span class="time-info">{html_escape(simplified_time)}</span>'
                    )

                # Process appearance count
                count_info = title_data.get("count", 1)
                if count_info > 1:
                    html += f'<span class="count-info">{count_info}x</span>'

                html += """
                            </div>
                            <div class="news-title">"""

                # Process title and link
                escaped_title = html_escape(title_data["title"])
                link_url = title_data.get("mobile_url") or title_data.get("url", "")

                if link_url:
                    escaped_url = html_escape(link_url)
                    html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                else:
                    html += escaped_title

                html += """
                            </div>
                        </div>
                    </div>"""

            html += """
                </div>"""

    # Process new news section
    if report_data["new_titles"]:
        html += f"""
                <div class="new-section">
                    <div class="new-section-title">Latest New Trending Topics ({report_data['total_new_count']} items)</div>"""

        for source_data in report_data["new_titles"]:
            escaped_source = html_escape(source_data["source_name"])
            titles_count = len(source_data["titles"])

            html += f"""
                    <div class="new-source-group">
                        <div class="new-source-title">{escaped_source} · {titles_count} items</div>"""

            # Add numbering for new news as well
            for idx, title_data in enumerate(source_data["titles"], 1):
                ranks = title_data.get("ranks", [])

                # Process rank display for new news
                rank_class = ""
                if ranks:
                    min_rank = min(ranks)
                    if min_rank <= 3:
                        rank_class = "top"
                    elif min_rank <= title_data.get("rank_threshold", 10):
                        rank_class = "high"

                    if len(ranks) == 1:
                        rank_text = str(ranks[0])
                    else:
                        rank_text = f"{min(ranks)}-{max(ranks)}"
                else:
                    rank_text = "?"

                html += f"""
                        <div class="new-item">
                            <div class="new-item-number">{idx}</div>
                            <div class="new-item-rank {rank_class}">{rank_text}</div>
                            <div class="new-item-content">
                                <div class="new-item-title">"""

                # Process link for new news
                escaped_title = html_escape(title_data["title"])
                link_url = title_data.get("mobile_url") or title_data.get("url", "")

                if link_url:
                    escaped_url = html_escape(link_url)
                    html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                else:
                    html += escaped_title

                html += """
                                </div>
                            </div>
                        </div>"""

            html += """
                    </div>"""

        html += """
                </div>"""

    html += """
            </div>
            
            <div class="footer">
                <div class="footer-content">
                    Generated by <span class="project-name">TrendRadar</span> ·
                    <a href="https://github.com/sansan0/TrendRadar" target="_blank" class="footer-link">
                        GitHub Open Source Project
                    </a>"""

    if update_info:
        html += f"""
                    <br>
                    <span style="color: #ea580c; font-weight: 500;">
                        New version {update_info['remote_version']} available, current version {update_info['current_version']}
                    </span>"""

    html += """
                </div>
            </div>
        </div>
        
        <script>
            async function saveAsImage() {
                const button = event.target;
                const originalText = button.textContent;
                
                try {
                    button.textContent = 'Generating...';
                    button.disabled = true;
                    window.scrollTo(0, 0);

                    // Wait for page to stabilize
                    await new Promise(resolve => setTimeout(resolve, 200));

                    // Hide buttons before screenshot
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'hidden';

                    // Wait again to ensure buttons are fully hidden
                    await new Promise(resolve => setTimeout(resolve, 100));
                    
                    const container = document.querySelector('.container');
                    
                    const canvas = await html2canvas(container, {
                        backgroundColor: '#ffffff',
                        scale: 1.5,
                        useCORS: true,
                        allowTaint: false,
                        imageTimeout: 10000,
                        removeContainer: false,
                        foreignObjectRendering: false,
                        logging: false,
                        width: container.offsetWidth,
                        height: container.offsetHeight,
                        x: 0,
                        y: 0,
                        scrollX: 0,
                        scrollY: 0,
                        windowWidth: window.innerWidth,
                        windowHeight: window.innerHeight
                    });
                    
                    buttons.style.visibility = 'visible';
                    
                    const link = document.createElement('a');
                    const now = new Date();
                    const filename = `TrendRadar_Trending_News_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}.png`;
                    
                    link.download = filename;
                    link.href = canvas.toDataURL('image/png', 1.0);
                    
                    // 触发下载
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    
                    button.textContent = '保存Success!';
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);
                    
                } catch (error) {
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'visible';
                    button.textContent = '保存Failed';
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);
                }
            }
            
            async function saveAsMultipleImages() {
                const button = event.target;
                const originalText = button.textContent;
                const container = document.querySelector('.container');
                const scale = 1.5; 
                const maxHeight = 5000 / scale;
                
                try {
                    button.textContent = 'Analyzing...';
                    button.disabled = true;

                    // Get all possible split elements
                    const newsItems = Array.from(container.querySelectorAll('.news-item'));
                    const wordGroups = Array.from(container.querySelectorAll('.word-group'));
                    const newSection = container.querySelector('.new-section');
                    const errorSection = container.querySelector('.error-section');
                    const header = container.querySelector('.header');
                    const footer = container.querySelector('.footer');
                    
                    // Calculate element positions and heights
                    const containerRect = container.getBoundingClientRect();
                    const elements = [];

                    // Add header as a required element
                    elements.push({
                        type: 'header',
                        element: header,
                        top: 0,
                        bottom: header.offsetHeight,
                        height: header.offsetHeight
                    });
                    
                    // Add error information (if exists)
                    if (errorSection) {
                        const rect = errorSection.getBoundingClientRect();
                        elements.push({
                            type: 'error',
                            element: errorSection,
                            top: rect.top - containerRect.top,
                            bottom: rect.bottom - containerRect.top,
                            height: rect.height
                        });
                    }
                    
                    // Process news-items by word-group
                    wordGroups.forEach(group => {
                        const groupRect = group.getBoundingClientRect();
                        const groupNewsItems = group.querySelectorAll('.news-item');

                        // Add word-group header section
                        const wordHeader = group.querySelector('.word-header');
                        if (wordHeader) {
                            const headerRect = wordHeader.getBoundingClientRect();
                            elements.push({
                                type: 'word-header',
                                element: wordHeader,
                                parent: group,
                                top: groupRect.top - containerRect.top,
                                bottom: headerRect.bottom - containerRect.top,
                                height: headerRect.height
                            });
                        }
                        
                        // Add each news-item
                        groupNewsItems.forEach(item => {
                            const rect = item.getBoundingClientRect();
                            elements.push({
                                type: 'news-item',
                                element: item,
                                parent: group,
                                top: rect.top - containerRect.top,
                                bottom: rect.bottom - containerRect.top,
                                height: rect.height
                            });
                        });
                    });
                    
                    // Add new news section
                    if (newSection) {
                        const rect = newSection.getBoundingClientRect();
                        elements.push({
                            type: 'new-section',
                            element: newSection,
                            top: rect.top - containerRect.top,
                            bottom: rect.bottom - containerRect.top,
                            height: rect.height
                        });
                    }
                    
                    // Add footer
                    const footerRect = footer.getBoundingClientRect();
                    elements.push({
                        type: 'footer',
                        element: footer,
                        top: footerRect.top - containerRect.top,
                        bottom: footerRect.bottom - containerRect.top,
                        height: footer.offsetHeight
                    });
                    
                    // Calculate split points
                    const segments = [];
                    let currentSegment = { start: 0, end: 0, height: 0, includeHeader: true };
                    let headerHeight = header.offsetHeight;
                    currentSegment.height = headerHeight;
                    
                    for (let i = 1; i < elements.length; i++) {
                        const element = elements[i];
                        const potentialHeight = element.bottom - currentSegment.start;
                        
                        // Check if new segment is needed
                        if (potentialHeight > maxHeight && currentSegment.height > headerHeight) {
                            // Split at previous element's end
                            currentSegment.end = elements[i - 1].bottom;
                            segments.push(currentSegment);

                            // Start new segment
                            currentSegment = {
                                start: currentSegment.end,
                                end: 0,
                                height: element.bottom - currentSegment.end,
                                includeHeader: false
                            };
                        } else {
                            currentSegment.height = potentialHeight;
                            currentSegment.end = element.bottom;
                        }
                    }
                    
                    // Add last segment
                    if (currentSegment.height > 0) {
                        currentSegment.end = container.offsetHeight;
                        segments.push(currentSegment);
                    }
                    
                    button.textContent = `Generating (0/${segments.length})...`;

                    // Hide save buttons
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'hidden';

                    // Generate image for each segment
                    const images = [];
                    for (let i = 0; i < segments.length; i++) {
                        const segment = segments[i];
                        button.textContent = `Generating (${i + 1}/${segments.length})...`;
                        
                        // Create temporary container for screenshot
                        const tempContainer = document.createElement('div');
                        tempContainer.style.cssText = `
                            position: absolute;
                            left: -9999px;
                            top: 0;
                            width: ${container.offsetWidth}px;
                            background: white;
                        `;
                        tempContainer.className = 'container';
                        
                        // Clone container content
                        const clonedContainer = container.cloneNode(true);

                        // Remove save buttons from cloned content
                        const clonedButtons = clonedContainer.querySelector('.save-buttons');
                        if (clonedButtons) {
                            clonedButtons.style.display = 'none';
                        }
                        
                        tempContainer.appendChild(clonedContainer);
                        document.body.appendChild(tempContainer);
                        
                        // Wait for DOM update
                        await new Promise(resolve => setTimeout(resolve, 100));
                        
                        // Use html2canvas to capture specific area
                        const canvas = await html2canvas(clonedContainer, {
                            backgroundColor: '#ffffff',
                            scale: scale,
                            useCORS: true,
                            allowTaint: false,
                            imageTimeout: 10000,
                            logging: false,
                            width: container.offsetWidth,
                            height: segment.end - segment.start,
                            x: 0,
                            y: segment.start,
                            windowWidth: window.innerWidth,
                            windowHeight: window.innerHeight
                        });
                        
                        images.push(canvas.toDataURL('image/png', 1.0));
                        
                        // Clean up temporary container
                        document.body.removeChild(tempContainer);
                    }
                    
                    // Restore button visibility
                    buttons.style.visibility = 'visible';

                    // Download all images
                    const now = new Date();
                    const baseFilename = `TrendRadar_Trending_News_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;
                    
                    for (let i = 0; i < images.length; i++) {
                        const link = document.createElement('a');
                        link.download = `${baseFilename}_part${i + 1}.png`;
                        link.href = images[i];
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        
                        // Delay to avoid browser blocking multiple downloads
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }

                    button.textContent = `Saved ${segments.length} images!`;
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);
                    
                } catch (error) {
                    console.error('Segment save failed:', error);
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'visible';
                    button.textContent = 'Save failed';
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);
                }
            }
            
            document.addEventListener('DOMContentLoaded', function() {
                window.scrollTo(0, 0);
            });
        </script>
    </body>
    </html>
    """

    return html


def render_feishu_content(
    report_data: Dict, update_info: Optional[Dict] = None, mode: str = "daily"
) -> str:
    """Render Feishu content"""
    text_content = ""

    if report_data["stats"]:
        text_content += f"📊 **热点词汇统计**\n\n"

    total_count = len(report_data["stats"])

    for i, stat in enumerate(report_data["stats"]):
        word = stat["word"]
        count = stat["count"]

        sequence_display = f"<font color='grey'>[{i + 1}/{total_count}]</font>"

        if count >= 10:
            text_content += f"🔥 {sequence_display} **{word}** : <font color='red'>{count}</font> 条\n\n"
        elif count >= 5:
            text_content += f"📈 {sequence_display} **{word}** : <font color='orange'>{count}</font> 条\n\n"
        else:
            text_content += f"📌 {sequence_display} **{word}** : {count} 条\n\n"

        for j, title_data in enumerate(stat["titles"], 1):
            formatted_title = format_title_for_platform(
                "feishu", title_data, show_source=True
            )
            text_content += f"  {j}. {formatted_title}\n"

            if j < len(stat["titles"]):
                text_content += "\n"

        if i < len(report_data["stats"]) - 1:
            text_content += f"\n{CONFIG['FEISHU_MESSAGE_SEPARATOR']}\n\n"

    if not text_content:
        if mode == "incremental":
            mode_text = "No new matching trending keywords in incremental mode"
        elif mode == "current":
            mode_text = "No matching trending keywords in current ranking mode"
        else:
            mode_text = "No matching trending keywords"
        text_content = f"📭 {mode_text}\n\n"

    if report_data["new_titles"]:
        if text_content and "No matching" not in text_content:
            text_content += f"\n{CONFIG['FEISHU_MESSAGE_SEPARATOR']}\n\n"

        text_content += (
            f"🆕 **Latest New Trending Topics** ({report_data['total_new_count']} items)\n\n"
        )

        for source_data in report_data["new_titles"]:
            text_content += (
                f"**{source_data['source_name']}** ({len(source_data['titles'])} items):\n"
            )

            for j, title_data in enumerate(source_data["titles"], 1):
                title_data_copy = title_data.copy()
                title_data_copy["is_new"] = False
                formatted_title = format_title_for_platform(
                    "feishu", title_data_copy, show_source=False
                )
                text_content += f"  {j}. {formatted_title}\n"

            text_content += "\n"

    if report_data["failed_ids"]:
        if text_content and "No matching" not in text_content:
            text_content += f"\n{CONFIG['FEISHU_MESSAGE_SEPARATOR']}\n\n"

        text_content += "⚠️ **Failed Platforms:**\n\n"
        for i, id_value in enumerate(report_data["failed_ids"], 1):
            text_content += f"  • <font color='red'>{id_value}</font>\n"

    now = get_utc_time()
    text_content += (
        f"\n\n<font color='grey'>Updated: {now.strftime('%Y-%m-%d %H:%M:%S')}</font>"
    )

    if update_info:
        text_content += f"\n<font color='grey'>TrendRadar new version {update_info['remote_version']} available, current {update_info['current_version']}</font>"

    return text_content


def render_dingtalk_content(
    report_data: Dict, update_info: Optional[Dict] = None, mode: str = "daily"
) -> str:
    """Render DingTalk content"""
    text_content = ""

    total_titles = sum(
        len(stat["titles"]) for stat in report_data["stats"] if stat["count"] > 0
    )
    now = get_utc_time()

    text_content += f"**Total News:** {total_titles}\n\n"
    text_content += f"**Time:** {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    text_content += f"**Type:** Trending Topics Analysis Report\n\n"

    text_content += "---\n\n"

    if report_data["stats"]:
        text_content += f"📊 **Trending Keywords Statistics**\n\n"

        total_count = len(report_data["stats"])

        for i, stat in enumerate(report_data["stats"]):
            word = stat["word"]
            count = stat["count"]

            sequence_display = f"[{i + 1}/{total_count}]"

            if count >= 10:
                text_content += f"🔥 {sequence_display} **{word}** : **{count}** 条\n\n"
            elif count >= 5:
                text_content += f"📈 {sequence_display} **{word}** : **{count}** 条\n\n"
            else:
                text_content += f"📌 {sequence_display} **{word}** : {count} 条\n\n"

            for j, title_data in enumerate(stat["titles"], 1):
                formatted_title = format_title_for_platform(
                    "dingtalk", title_data, show_source=True
                )
                text_content += f"  {j}. {formatted_title}\n"

                if j < len(stat["titles"]):
                    text_content += "\n"

            if i < len(report_data["stats"]) - 1:
                text_content += f"\n---\n\n"

    if not report_data["stats"]:
        if mode == "incremental":
            mode_text = "No new matching trending keywords in incremental mode"
        elif mode == "current":
            mode_text = "No matching trending keywords in current ranking mode"
        else:
            mode_text = "No matching trending keywords"
        text_content += f"📭 {mode_text}\n\n"

    if report_data["new_titles"]:
        if text_content and "No matching" not in text_content:
            text_content += f"\n---\n\n"

        text_content += (
            f"🆕 **Latest New Trending Topics** ({report_data['total_new_count']} items)\n\n"
        )

        for source_data in report_data["new_titles"]:
            text_content += f"**{source_data['source_name']}** ({len(source_data['titles'])} items):\n\n"

            for j, title_data in enumerate(source_data["titles"], 1):
                title_data_copy = title_data.copy()
                title_data_copy["is_new"] = False
                formatted_title = format_title_for_platform(
                    "dingtalk", title_data_copy, show_source=False
                )
                text_content += f"  {j}. {formatted_title}\n"

            text_content += "\n"

    if report_data["failed_ids"]:
        if text_content and "No matching" not in text_content:
            text_content += f"\n---\n\n"

        text_content += "⚠️ **Failed Platforms:**\n\n"
        for i, id_value in enumerate(report_data["failed_ids"], 1):
            text_content += f"  • **{id_value}**\n"

    text_content += f"\n\n> Updated: {now.strftime('%Y-%m-%d %H:%M:%S')}"

    if update_info:
        text_content += f"\n> TrendRadar new version **{update_info['remote_version']}** available, current **{update_info['current_version']}**"

    return text_content


def split_content_into_batches(
    report_data: Dict,
    format_type: str,
    update_info: Optional[Dict] = None,
    max_bytes: int = None,
    mode: str = "daily",
) -> List[str]:
    """Split message content into batches, ensuring word group title + at least one news item integrity"""
    if max_bytes is None:
        if format_type == "dingtalk":
            max_bytes = CONFIG.get("DINGTALK_BATCH_SIZE", 20000)
        elif format_type == "feishu":
            max_bytes = CONFIG.get("FEISHU_BATCH_SIZE", 29000)
        elif format_type == "ntfy":
            max_bytes = 3800
        else:
            max_bytes = CONFIG.get("MESSAGE_BATCH_SIZE", 4000)

    batches = []

    total_titles = sum(
        len(stat["titles"]) for stat in report_data["stats"] if stat["count"] > 0
    )
    now = get_utc_time()

    base_header = ""
    if format_type == "wework":
        base_header = f"**Total News:** {total_titles}\n\n\n\n"
    elif format_type == "telegram":
        base_header = f"Total News: {total_titles}\n\n"
    elif format_type == "ntfy":
        base_header = f"**Total News:** {total_titles}\n\n"
    elif format_type == "feishu":
        base_header = ""
    elif format_type == "dingtalk":
        base_header = f"**Total News:** {total_titles}\n\n"
        base_header += f"**Time:** {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        base_header += f"**Type:** Trending Topics Analysis Report\n\n"
        base_header += "---\n\n"

    base_footer = ""
    if format_type == "wework":
        base_footer = f"\n\n\n> Updated: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        if update_info:
            base_footer += f"\n> TrendRadar new version **{update_info['remote_version']}** available, current **{update_info['current_version']}**"
    elif format_type == "telegram":
        base_footer = f"\n\nUpdated: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        if update_info:
            base_footer += f"\nTrendRadar new version {update_info['remote_version']} available, current {update_info['current_version']}"
    elif format_type == "ntfy":
        base_footer = f"\n\n> Updated: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        if update_info:
            base_footer += f"\n> TrendRadar new version **{update_info['remote_version']}** available, current **{update_info['current_version']}**"
    elif format_type == "feishu":
        base_footer = f"\n\n<font color='grey'>Updated: {now.strftime('%Y-%m-%d %H:%M:%S')}</font>"
        if update_info:
            base_footer += f"\n<font color='grey'>TrendRadar new version {update_info['remote_version']} available, current {update_info['current_version']}</font>"
    elif format_type == "dingtalk":
        base_footer = f"\n\n> Updated: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        if update_info:
            base_footer += f"\n> TrendRadar new version **{update_info['remote_version']}** available, current **{update_info['current_version']}**"

    stats_header = ""
    if report_data["stats"]:
        if format_type == "wework":
            stats_header = f"📊 **Trending Keywords Statistics**\n\n"
        elif format_type == "telegram":
            stats_header = f"📊 Trending Keywords Statistics\n\n"
        elif format_type == "ntfy":
            stats_header = f"📊 **Trending Keywords Statistics**\n\n"
        elif format_type == "feishu":
            stats_header = f"📊 **Trending Keywords Statistics**\n\n"
        elif format_type == "dingtalk":
            stats_header = f"📊 **Trending Keywords Statistics**\n\n"

    current_batch = base_header
    current_batch_has_content = False

    if (
        not report_data["stats"]
        and not report_data["new_titles"]
        and not report_data["failed_ids"]
    ):
        if mode == "incremental":
            mode_text = "No new matching trending keywords in incremental mode"
        elif mode == "current":
            mode_text = "No matching trending keywords in current ranking mode"
        else:
            mode_text = "No matching trending keywords"
        simple_content = f"📭 {mode_text}\n\n"
        final_content = base_header + simple_content + base_footer
        batches.append(final_content)
        return batches

    # Process hot keywords statistics
    if report_data["stats"]:
        total_count = len(report_data["stats"])

        # 添加统计Title
        test_content = current_batch + stats_header
        if (
            len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
            < max_bytes
        ):
            current_batch = test_content
            current_batch_has_content = True
        else:
            if current_batch_has_content:
                batches.append(current_batch + base_footer)
            current_batch = base_header + stats_header
            current_batch_has_content = True

        # 逐个处理词组（确保词组Title+Batch一条新闻的原子性）
        for i, stat in enumerate(report_data["stats"]):
            word = stat["word"]
            count = stat["count"]
            sequence_display = f"[{i + 1}/{total_count}]"

            # 构建词组Title
            word_header = ""
            if format_type == "wework":
                if count >= 10:
                    word_header = (
                        f"🔥 {sequence_display} **{word}** : **{count}** 条\n\n"
                    )
                elif count >= 5:
                    word_header = (
                        f"📈 {sequence_display} **{word}** : **{count}** 条\n\n"
                    )
                else:
                    word_header = f"📌 {sequence_display} **{word}** : {count} 条\n\n"
            elif format_type == "telegram":
                if count >= 10:
                    word_header = f"🔥 {sequence_display} {word} : {count} 条\n\n"
                elif count >= 5:
                    word_header = f"📈 {sequence_display} {word} : {count} 条\n\n"
                else:
                    word_header = f"📌 {sequence_display} {word} : {count} 条\n\n"
            elif format_type == "ntfy":
                if count >= 10:
                    word_header = (
                        f"🔥 {sequence_display} **{word}** : **{count}** 条\n\n"
                    )
                elif count >= 5:
                    word_header = (
                        f"📈 {sequence_display} **{word}** : **{count}** 条\n\n"
                    )
                else:
                    word_header = f"📌 {sequence_display} **{word}** : {count} 条\n\n"
            elif format_type == "feishu":
                if count >= 10:
                    word_header = f"🔥 <font color='grey'>{sequence_display}</font> **{word}** : <font color='red'>{count}</font> 条\n\n"
                elif count >= 5:
                    word_header = f"📈 <font color='grey'>{sequence_display}</font> **{word}** : <font color='orange'>{count}</font> 条\n\n"
                else:
                    word_header = f"📌 <font color='grey'>{sequence_display}</font> **{word}** : {count} 条\n\n"
            elif format_type == "dingtalk":
                if count >= 10:
                    word_header = (
                        f"🔥 {sequence_display} **{word}** : **{count}** 条\n\n"
                    )
                elif count >= 5:
                    word_header = (
                        f"📈 {sequence_display} **{word}** : **{count}** 条\n\n"
                    )
                else:
                    word_header = f"📌 {sequence_display} **{word}** : {count} 条\n\n"

            # 构建Batch一条新闻
            first_news_line = ""
            if stat["titles"]:
                first_title_data = stat["titles"][0]
                if format_type == "wework":
                    formatted_title = format_title_for_platform(
                        "wework", first_title_data, show_source=True
                    )
                elif format_type == "telegram":
                    formatted_title = format_title_for_platform(
                        "telegram", first_title_data, show_source=True
                    )
                elif format_type == "ntfy":
                    formatted_title = format_title_for_platform(
                        "ntfy", first_title_data, show_source=True
                    )
                elif format_type == "feishu":
                    formatted_title = format_title_for_platform(
                        "feishu", first_title_data, show_source=True
                    )
                elif format_type == "dingtalk":
                    formatted_title = format_title_for_platform(
                        "dingtalk", first_title_data, show_source=True
                    )
                else:
                    formatted_title = f"{first_title_data['title']}"

                first_news_line = f"  1. {formatted_title}\n"
                if len(stat["titles"]) > 1:
                    first_news_line += "\n"

            # 原子性检查：词组Title+Batch一条新闻必须一起处理
            word_with_first_news = word_header + first_news_line
            test_content = current_batch + word_with_first_news

            if (
                len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                >= max_bytes
            ):
                # 当前批times容纳不下，开启新批times
                if current_batch_has_content:
                    batches.append(current_batch + base_footer)
                current_batch = base_header + stats_header + word_with_first_news
                current_batch_has_content = True
                start_index = 1
            else:
                current_batch = test_content
                current_batch_has_content = True
                start_index = 1

            # Process remaining news items
            for j in range(start_index, len(stat["titles"])):
                title_data = stat["titles"][j]
                if format_type == "wework":
                    formatted_title = format_title_for_platform(
                        "wework", title_data, show_source=True
                    )
                elif format_type == "telegram":
                    formatted_title = format_title_for_platform(
                        "telegram", title_data, show_source=True
                    )
                elif format_type == "ntfy":
                    formatted_title = format_title_for_platform(
                        "ntfy", title_data, show_source=True
                    )
                elif format_type == "feishu":
                    formatted_title = format_title_for_platform(
                        "feishu", title_data, show_source=True
                    )
                elif format_type == "dingtalk":
                    formatted_title = format_title_for_platform(
                        "dingtalk", title_data, show_source=True
                    )
                else:
                    formatted_title = f"{title_data['title']}"

                news_line = f"  {j + 1}. {formatted_title}\n"
                if j < len(stat["titles"]) - 1:
                    news_line += "\n"

                test_content = current_batch + news_line
                if (
                    len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                    >= max_bytes
                ):
                    if current_batch_has_content:
                        batches.append(current_batch + base_footer)
                    current_batch = base_header + stats_header + word_header + news_line
                    current_batch_has_content = True
                else:
                    current_batch = test_content
                    current_batch_has_content = True

            # Separator between word groups
            if i < len(report_data["stats"]) - 1:
                separator = ""
                if format_type == "wework":
                    separator = f"\n\n\n\n"
                elif format_type == "telegram":
                    separator = f"\n\n"
                elif format_type == "ntfy":
                    separator = f"\n\n"
                elif format_type == "feishu":
                    separator = f"\n{CONFIG['FEISHU_MESSAGE_SEPARATOR']}\n\n"
                elif format_type == "dingtalk":
                    separator = f"\n---\n\n"

                test_content = current_batch + separator
                if (
                    len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                    < max_bytes
                ):
                    current_batch = test_content

    # 处理New新闻（同样确保SourceTitle+Batch一条新闻的原子性）
    if report_data["new_titles"]:
        new_header = ""
        if format_type == "wework":
            new_header = f"\n\n\n\n🆕 **本timesNew热点新闻** (共 {report_data['total_new_count']} 条)\n\n"
        elif format_type == "telegram":
            new_header = (
                f"\n\n🆕 本timesNew热点新闻 (共 {report_data['total_new_count']} 条)\n\n"
            )
        elif format_type == "ntfy":
            new_header = f"\n\n🆕 **本timesNew热点新闻** (共 {report_data['total_new_count']} 条)\n\n"
        elif format_type == "feishu":
            new_header = f"\n{CONFIG['FEISHU_MESSAGE_SEPARATOR']}\n\n🆕 **本timesNew热点新闻** (共 {report_data['total_new_count']} 条)\n\n"
        elif format_type == "dingtalk":
            new_header = f"\n---\n\n🆕 **本timesNew热点新闻** (共 {report_data['total_new_count']} 条)\n\n"

        test_content = current_batch + new_header
        if (
            len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
            >= max_bytes
        ):
            if current_batch_has_content:
                batches.append(current_batch + base_footer)
            current_batch = base_header + new_header
            current_batch_has_content = True
        else:
            current_batch = test_content
            current_batch_has_content = True

        # 逐个处理New新闻Source
        for source_data in report_data["new_titles"]:
            source_header = ""
            if format_type == "wework":
                source_header = f"**{source_data['source_name']}** ({len(source_data['titles'])} 条):\n\n"
            elif format_type == "telegram":
                source_header = f"{source_data['source_name']} ({len(source_data['titles'])} 条):\n\n"
            elif format_type == "ntfy":
                source_header = f"**{source_data['source_name']}** ({len(source_data['titles'])} 条):\n\n"
            elif format_type == "feishu":
                source_header = f"**{source_data['source_name']}** ({len(source_data['titles'])} 条):\n\n"
            elif format_type == "dingtalk":
                source_header = f"**{source_data['source_name']}** ({len(source_data['titles'])} 条):\n\n"

            # 构建Batch一条New新闻
            first_news_line = ""
            if source_data["titles"]:
                first_title_data = source_data["titles"][0]
                title_data_copy = first_title_data.copy()
                title_data_copy["is_new"] = False

                if format_type == "wework":
                    formatted_title = format_title_for_platform(
                        "wework", title_data_copy, show_source=False
                    )
                elif format_type == "telegram":
                    formatted_title = format_title_for_platform(
                        "telegram", title_data_copy, show_source=False
                    )
                elif format_type == "feishu":
                    formatted_title = format_title_for_platform(
                        "feishu", title_data_copy, show_source=False
                    )
                elif format_type == "dingtalk":
                    formatted_title = format_title_for_platform(
                        "dingtalk", title_data_copy, show_source=False
                    )
                else:
                    formatted_title = f"{title_data_copy['title']}"

                first_news_line = f"  1. {formatted_title}\n"

            # 原子性检查：SourceTitle+Batch一条新闻
            source_with_first_news = source_header + first_news_line
            test_content = current_batch + source_with_first_news

            if (
                len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                >= max_bytes
            ):
                if current_batch_has_content:
                    batches.append(current_batch + base_footer)
                current_batch = base_header + new_header + source_with_first_news
                current_batch_has_content = True
                start_index = 1
            else:
                current_batch = test_content
                current_batch_has_content = True
                start_index = 1

            # 处理剩余New新闻
            for j in range(start_index, len(source_data["titles"])):
                title_data = source_data["titles"][j]
                title_data_copy = title_data.copy()
                title_data_copy["is_new"] = False

                if format_type == "wework":
                    formatted_title = format_title_for_platform(
                        "wework", title_data_copy, show_source=False
                    )
                elif format_type == "telegram":
                    formatted_title = format_title_for_platform(
                        "telegram", title_data_copy, show_source=False
                    )
                elif format_type == "feishu":
                    formatted_title = format_title_for_platform(
                        "feishu", title_data_copy, show_source=False
                    )
                elif format_type == "dingtalk":
                    formatted_title = format_title_for_platform(
                        "dingtalk", title_data_copy, show_source=False
                    )
                else:
                    formatted_title = f"{title_data_copy['title']}"

                news_line = f"  {j + 1}. {formatted_title}\n"

                test_content = current_batch + news_line
                if (
                    len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                    >= max_bytes
                ):
                    if current_batch_has_content:
                        batches.append(current_batch + base_footer)
                    current_batch = base_header + new_header + source_header + news_line
                    current_batch_has_content = True
                else:
                    current_batch = test_content
                    current_batch_has_content = True

            current_batch += "\n"

    if report_data["failed_ids"]:
        failed_header = ""
        if format_type == "wework":
            failed_header = f"\n\n\n\n⚠️ **数据获取Failed Platforms:**\n\n"
        elif format_type == "telegram":
            failed_header = f"\n\n⚠️ 数据获取Failed Platforms:\n\n"
        elif format_type == "ntfy":
            failed_header = f"\n\n⚠️ **数据获取Failed Platforms:**\n\n"
        elif format_type == "feishu":
            failed_header = f"\n{CONFIG['FEISHU_MESSAGE_SEPARATOR']}\n\n⚠️ **数据获取Failed Platforms:**\n\n"
        elif format_type == "dingtalk":
            failed_header = f"\n---\n\n⚠️ **数据获取Failed Platforms:**\n\n"

        test_content = current_batch + failed_header
        if (
            len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
            >= max_bytes
        ):
            if current_batch_has_content:
                batches.append(current_batch + base_footer)
            current_batch = base_header + failed_header
            current_batch_has_content = True
        else:
            current_batch = test_content
            current_batch_has_content = True

        for i, id_value in enumerate(report_data["failed_ids"], 1):
            if format_type == "feishu":
                failed_line = f"  • <font color='red'>{id_value}</font>\n"
            elif format_type == "dingtalk":
                failed_line = f"  • **{id_value}**\n"
            else:
                failed_line = f"  • {id_value}\n"

            test_content = current_batch + failed_line
            if (
                len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                >= max_bytes
            ):
                if current_batch_has_content:
                    batches.append(current_batch + base_footer)
                current_batch = base_header + failed_header + failed_line
                current_batch_has_content = True
            else:
                current_batch = test_content
                current_batch_has_content = True

    # 完成最后批times
    if current_batch_has_content:
        batches.append(current_batch + base_footer)

    return batches


def send_to_notifications(
    stats: List[Dict],
    failed_ids: Optional[List] = None,
    report_type: str = "Daily Summary",
    new_titles: Optional[Dict] = None,
    id_to_name: Optional[Dict] = None,
    update_info: Optional[Dict] = None,
    proxy_url: Optional[str] = None,
    mode: str = "daily",
    html_file_path: Optional[str] = None,
) -> Dict[str, bool]:
    """Send data to multiple notification platforms"""
    results = {}

    if CONFIG["PUSH_WINDOW"]["ENABLED"]:
        push_manager = PushRecordManager()
        time_range_start = CONFIG["PUSH_WINDOW"]["TIME_RANGE"]["START"]
        time_range_end = CONFIG["PUSH_WINDOW"]["TIME_RANGE"]["END"]

        if not push_manager.is_in_time_range(time_range_start, time_range_end):
            now = get_utc_time()
            print(
                f"推送窗口控制：当前Time {now.strftime('%H:%M')} not within push time window {time_range_start}-{time_range_end} , skipping push"
            )
            return results

        if CONFIG["PUSH_WINDOW"]["ONCE_PER_DAY"]:
            if push_manager.has_pushed_recently(cooldown_hours=23):
                print(f"Push window: sent within last 23h, skipping to prevent cross-day duplicate")
                return results
            else:
                print(f"Push window: no push in last 23h, proceeding")

    report_data = prepare_report_data(stats, failed_ids, new_titles, id_to_name, mode)

    feishu_url = CONFIG["FEISHU_WEBHOOK_URL"]
    dingtalk_url = CONFIG["DINGTALK_WEBHOOK_URL"]
    wework_url = CONFIG["WEWORK_WEBHOOK_URL"]
    telegram_token = CONFIG["TELEGRAM_BOT_TOKEN"]
    telegram_chat_id = CONFIG["TELEGRAM_CHAT_ID"]
    email_from = CONFIG["EMAIL_FROM"]
    email_password = CONFIG["EMAIL_PASSWORD"]
    email_to = CONFIG["EMAIL_TO"]
    email_smtp_server = CONFIG.get("EMAIL_SMTP_SERVER", "")
    email_smtp_port = CONFIG.get("EMAIL_SMTP_PORT", "")
    ntfy_server_url = CONFIG["NTFY_SERVER_URL"]
    ntfy_topic = CONFIG["NTFY_TOPIC"]
    ntfy_token = CONFIG.get("NTFY_TOKEN", "")

    update_info_to_send = update_info if CONFIG["SHOW_VERSION_UPDATE"] else None

    # 发送到飞书
    if feishu_url:
        results["feishu"] = send_to_feishu(
            feishu_url, report_data, report_type, update_info_to_send, proxy_url, mode
        )

    # 发送到钉钉
    if dingtalk_url:
        results["dingtalk"] = send_to_dingtalk(
            dingtalk_url, report_data, report_type, update_info_to_send, proxy_url, mode
        )

    # 发送到企业微信
    if wework_url:
        results["wework"] = send_to_wework(
            wework_url, report_data, report_type, update_info_to_send, proxy_url, mode
        )

    # 发送到 Telegram
    if telegram_token and telegram_chat_id:
        results["telegram"] = send_to_telegram(
            telegram_token,
            telegram_chat_id,
            report_data,
            report_type,
            update_info_to_send,
            proxy_url,
            mode,
        )

    # 发送到 ntfy
    if ntfy_server_url and ntfy_topic:
        results["ntfy"] = send_to_ntfy(
            ntfy_server_url,
            ntfy_topic,
            ntfy_token,
            report_data,
            report_type,
            update_info_to_send,
            proxy_url,
            mode,
        )

    # 发送邮件
    if email_from and email_password and email_to:
        results["email"] = send_to_email(
            email_from,
            email_password,
            email_to,
            report_type,
            html_file_path,
            email_smtp_server,
            email_smtp_port,
            report_data,
            mode,
        )

    if not results:
        print("No notification channels configured, skipping notification")

    # 如果Success发送了任何通知，且启用了每天只推一times，则记录推送
    if (
        CONFIG["PUSH_WINDOW"]["ENABLED"]
        and CONFIG["PUSH_WINDOW"]["ONCE_PER_DAY"]
        and any(results.values())
    ):
        push_manager = PushRecordManager()
        push_manager.record_push(report_type)

    return results


def send_to_feishu(
    webhook_url: str,
    report_data: Dict,
    report_type: str,
    update_info: Optional[Dict] = None,
    proxy_url: Optional[str] = None,
    mode: str = "daily",
) -> bool:
    """Send to Feishu (supports batch sending)"""
    headers = {"Content-Type": "application/json"}
    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    # 获取分批内容，使用飞书专用的批times大小
    batches = split_content_into_batches(
        report_data,
        "feishu",
        update_info,
        max_bytes=CONFIG.get("FEISHU_BATCH_SIZE", 29000),
        mode=mode,
    )

    print(f"Feishu message divided into {len(batches)} 批times发送 [{report_type}]")

    # 逐批发送
    for i, batch_content in enumerate(batches, 1):
        batch_size = len(batch_content.encode("utf-8"))
        print(
            f"发送飞书Batch {i}/{len(batches)} 批times，大小：{batch_size} 字节 [{report_type}]"
        )

        # 添加批times标识
        if len(batches) > 1:
            batch_header = f"**[Batch {i}/{len(batches)} 批times]**\n\n"
            # 将批times标识插入到适当位置（在统计Title之后）
            if "📊 **热点词汇统计**" in batch_content:
                batch_content = batch_content.replace(
                    "📊 **热点词汇统计**\n\n", f"📊 **热点词汇统计** {batch_header}"
                )
            else:
                # 如果没有统计Title，直接在开头添加
                batch_content = batch_header + batch_content

        total_titles = sum(
            len(stat["titles"]) for stat in report_data["stats"] if stat["count"] > 0
        )
        now = get_utc_time()

        payload = {
            "msg_type": "text",
            "content": {
                "total_titles": total_titles,
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "report_type": report_type,
                "text": batch_content,
            },
        }

        try:
            response = requests.post(
                webhook_url, headers=headers, json=payload, proxies=proxies, timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                # 检查飞书的响应状态
                if result.get("StatusCode") == 0 or result.get("code") == 0:
                    print(f"飞书Batch {i}/{len(batches)} 批times发送Success [{report_type}]")
                    # 批times间间隔
                    if i < len(batches):
                        time.sleep(CONFIG["BATCH_SEND_INTERVAL"])
                else:
                    error_msg = result.get("msg") or result.get("StatusMessage", "未知Error")
                    print(
                        f"飞书Batch {i}/{len(batches)} 批times发送Failed [{report_type}]，Error：{error_msg}"
                    )
                    return False
            else:
                print(
                    f"飞书Batch {i}/{len(batches)} 批times发送Failed [{report_type}]，状态码：{response.status_code}"
                )
                return False
        except Exception as e:
            print(f"飞书Batch {i}/{len(batches)} 批times发送出错 [{report_type}]：{e}")
            return False

    print(f"飞书All {len(batches)} 批times发送完成 [{report_type}]")
    return True


def send_to_dingtalk(
    webhook_url: str,
    report_data: Dict,
    report_type: str,
    update_info: Optional[Dict] = None,
    proxy_url: Optional[str] = None,
    mode: str = "daily",
) -> bool:
    """Send to DingTalk (supports batch sending)"""
    headers = {"Content-Type": "application/json"}
    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    # 获取分批内容，使用钉钉专用的批times大小
    batches = split_content_into_batches(
        report_data,
        "dingtalk",
        update_info,
        max_bytes=CONFIG.get("DINGTALK_BATCH_SIZE", 20000),
        mode=mode,
    )

    print(f"DingTalk message divided into {len(batches)} 批times发送 [{report_type}]")

    # 逐批发送
    for i, batch_content in enumerate(batches, 1):
        batch_size = len(batch_content.encode("utf-8"))
        print(
            f"发送钉钉Batch {i}/{len(batches)} 批times，大小：{batch_size} 字节 [{report_type}]"
        )

        # 添加批times标识
        if len(batches) > 1:
            batch_header = f"**[Batch {i}/{len(batches)} 批times]**\n\n"
            # 将批times标识插入到适当位置（在Title之后）
            if "📊 **热点词汇统计**" in batch_content:
                batch_content = batch_content.replace(
                    "📊 **热点词汇统计**\n\n", f"📊 **热点词汇统计** {batch_header}\n\n"
                )
            else:
                # 如果没有统计Title，直接在开头添加
                batch_content = batch_header + batch_content

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"TrendRadar Hot Topics Analysis Report - {report_type}",
                "text": batch_content,
            },
        }

        try:
            response = requests.post(
                webhook_url, headers=headers, json=payload, proxies=proxies, timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    print(f"钉钉Batch {i}/{len(batches)} 批times发送Success [{report_type}]")
                    # 批times间间隔
                    if i < len(batches):
                        time.sleep(CONFIG["BATCH_SEND_INTERVAL"])
                else:
                    print(
                        f"钉钉Batch {i}/{len(batches)} 批times发送Failed [{report_type}]，Error：{result.get('errmsg')}"
                    )
                    return False
            else:
                print(
                    f"钉钉Batch {i}/{len(batches)} 批times发送Failed [{report_type}]，状态码：{response.status_code}"
                )
                return False
        except Exception as e:
            print(f"钉钉Batch {i}/{len(batches)} 批times发送出错 [{report_type}]：{e}")
            return False

    print(f"钉钉All {len(batches)} 批times发送完成 [{report_type}]")
    return True


def send_to_wework(
    webhook_url: str,
    report_data: Dict,
    report_type: str,
    update_info: Optional[Dict] = None,
    proxy_url: Optional[str] = None,
    mode: str = "daily",
) -> bool:
    """Send to WeWork (supports batch sending)"""
    headers = {"Content-Type": "application/json"}
    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    # 获取分批内容
    batches = split_content_into_batches(report_data, "wework", update_info, mode=mode)

    print(f"WeWork message divided into {len(batches)} 批times发送 [{report_type}]")

    # 逐批发送
    for i, batch_content in enumerate(batches, 1):
        batch_size = len(batch_content.encode("utf-8"))
        print(
            f"发送企业微信Batch {i}/{len(batches)} 批times，大小：{batch_size} 字节 [{report_type}]"
        )

        # 添加批times标识
        if len(batches) > 1:
            batch_header = f"**[Batch {i}/{len(batches)} 批times]**\n\n"
            batch_content = batch_header + batch_content

        payload = {"msgtype": "markdown", "markdown": {"content": batch_content}}

        try:
            response = requests.post(
                webhook_url, headers=headers, json=payload, proxies=proxies, timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    print(f"企业微信Batch {i}/{len(batches)} 批times发送Success [{report_type}]")
                    # 批times间间隔
                    if i < len(batches):
                        time.sleep(CONFIG["BATCH_SEND_INTERVAL"])
                else:
                    print(
                        f"企业微信Batch {i}/{len(batches)} 批times发送Failed [{report_type}]，Error：{result.get('errmsg')}"
                    )
                    return False
            else:
                print(
                    f"企业微信Batch {i}/{len(batches)} 批times发送Failed [{report_type}]，状态码：{response.status_code}"
                )
                return False
        except Exception as e:
            print(f"企业微信Batch {i}/{len(batches)} 批times发送出错 [{report_type}]：{e}")
            return False

    print(f"企业微信All {len(batches)} 批times发送完成 [{report_type}]")
    return True


def send_to_telegram(
    bot_token: str,
    chat_id: str,
    report_data: Dict,
    report_type: str,
    update_info: Optional[Dict] = None,
    proxy_url: Optional[str] = None,
    mode: str = "daily",
) -> bool:
    """Send to Telegram (supports batch sending)"""
    headers = {"Content-Type": "application/json"}
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    # 获取分批内容
    batches = split_content_into_batches(
        report_data, "telegram", update_info, mode=mode
    )

    print(f"Telegram message divided into {len(batches)} 批times发送 [{report_type}]")

    # 逐批发送
    for i, batch_content in enumerate(batches, 1):
        batch_size = len(batch_content.encode("utf-8"))
        print(
            f"发送TelegramBatch {i}/{len(batches)} 批times，大小：{batch_size} 字节 [{report_type}]"
        )

        # 添加批times标识
        if len(batches) > 1:
            batch_header = f"<b>[Batch {i}/{len(batches)} 批times]</b>\n\n"
            batch_content = batch_header + batch_content

        payload = {
            "chat_id": chat_id,
            "text": batch_content,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            response = requests.post(
                url, headers=headers, json=payload, proxies=proxies, timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    print(f"TelegramBatch {i}/{len(batches)} 批times发送Success [{report_type}]")
                    # 批times间间隔
                    if i < len(batches):
                        time.sleep(CONFIG["BATCH_SEND_INTERVAL"])
                else:
                    print(
                        f"TelegramBatch {i}/{len(batches)} 批times发送Failed [{report_type}]，Error：{result.get('description')}"
                    )
                    return False
            else:
                print(
                    f"TelegramBatch {i}/{len(batches)} 批times发送Failed [{report_type}]，状态码：{response.status_code}"
                )
                return False
        except Exception as e:
            print(f"TelegramBatch {i}/{len(batches)} 批times发送出错 [{report_type}]：{e}")
            return False

    print(f"TelegramAll {len(batches)} 批times发送完成 [{report_type}]")
    return True


def _render_email_category_card(stat: Dict) -> str:
    """Render a single category card for the email dual-column layout."""
    word = html_escape(stat["word"])
    count = stat["count"]
    titles = stat.get("titles", [])

    parts = [
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="background-color:#ffffff;border-radius:8px;border:1px solid #e2e8f0;'
        f'overflow:hidden;margin-bottom:16px;">'
        f'<tr><td style="padding:11px 14px 11px 17px;border-left:3px solid #6366f1;">'
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td><span style="font-size:13px;font-weight:700;color:#0f172a;">{word}</span></td>'
        f'<td align="right"><span style="font-size:10px;color:#94a3b8;font-weight:500;">'
        f'{count} items</span></td>'
        f'</tr></table></td></tr>'
        f'<tr><td style="padding:4px 14px 10px 14px;">'
    ]

    for idx, title_data in enumerate(titles):
        title = html_escape(title_data["title"])
        source = html_escape(title_data["source_name"])
        ranks = title_data.get("ranks", [])
        url = title_data.get("url", "")
        is_new = title_data.get("is_new", False)

        if ranks:
            mn, mx = min(ranks), max(ranks)
            rank_text = f"#{mn}" if mn == mx else f"#{mn}-{mx}"
        else:
            rank_text = ""

        row_bg = "#fffbeb" if is_new else "#f8fafc"
        new_dot = (
            '<span style="display:inline-block;width:6px;height:6px;'
            'background-color:#f59e0b;border-radius:50%;margin-right:4px;'
            'vertical-align:middle;"></span>'
            if is_new else ""
        )

        if url:
            title_html = (
                f'<a href="{html_escape(url)}" style="color:#1e293b;text-decoration:none;'
                f'font-weight:500;line-height:1.4;">{title}</a>'
            )
        else:
            title_html = f'<span style="color:#1e293b;font-weight:500;line-height:1.4;">{title}</span>'

        rank_html = (
            f'<span style="color:#6366f1;font-size:10px;font-weight:700;margin-left:4px;">'
            f'{rank_text}</span>'
            if rank_text else ""
        )

        sep = (
            '<tr><td colspan="2" style="padding:3px 0 0 0;border-top:1px solid #f1f5f9;'
            'font-size:0;line-height:0;">&nbsp;</td></tr>'
            if idx > 0 else ""
        )

        parts.append(
            f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="margin-top:6px;background-color:{row_bg};border-radius:4px;">'
            f'{sep}'
            f'<tr valign="top">'
            f'<td style="width:22px;padding:6px 4px 6px 2px;vertical-align:top;">'
            f'<span style="display:inline-block;background-color:#e2e8f0;color:#64748b;'
            f'font-size:10px;font-weight:700;width:18px;height:18px;line-height:18px;'
            f'text-align:center;border-radius:3px;">{idx + 1}</span>'
            f'</td>'
            f'<td style="padding:5px 0;vertical-align:top;">'
            f'<div style="margin-bottom:3px;">'
            f'<span style="background-color:#f1f5f9;color:#64748b;font-size:10px;'
            f'padding:2px 6px;border-radius:3px;">{source}</span>{rank_html}'
            f'</div>'
            f'<div style="font-size:13px;color:#1e293b;">{new_dot}{title_html}</div>'
            f'</td></tr></table>'
        )

    parts.append("</td></tr></table>")
    return "".join(parts)


def convert_to_gmail_html(
    original_html: str,
    report_data: Optional[Dict] = None,
    mode: str = "daily",
) -> str:
    """Build a responsive dual-column email from report_data."""
    if not report_data:
        return original_html

    stats = report_data.get("stats", [])
    total_titles = sum(len(s["titles"]) for s in stats if s.get("count", 0) > 0)
    total_categories = sum(1 for s in stats if s.get("count", 0) > 0)
    now = get_utc_time()
    date_str = now.strftime("%d %b %Y &middot; %H:%M")
    mode_label = {"daily": "DAILY", "incremental": "DELTA", "current": "CURRENT"}.get(
        mode, mode.upper()
    )

    html_parts = [
        f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
@media only screen and (max-width: 620px) {{
  .col-l, .col-r {{ display:block !important; width:100% !important;
                    padding-left:0 !important; padding-right:0 !important; }}
  .col-gap {{ display:none !important; }}
  .outer {{ padding:8px !important; }}
  .hdr {{ padding:16px 14px !important; }}
  .content {{ padding:12px 12px 4px 12px !important; }}
}}
</style>
</head>
<body style="margin:0;padding:0;background-color:#f1f5f9;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td align="center" class="outer" style="padding:24px 16px;">
  <table cellpadding="0" cellspacing="0" border="0"
    style="width:100%;max-width:800px;background-color:#ffffff;
    border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

    <!-- Header -->
    <tr>
      <td class="hdr" style="background-color:#0f172a;padding:20px 24px;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
          <td>
            <div style="font-size:20px;font-weight:700;color:#ffffff;letter-spacing:-0.3px;">
              &#x1F4CA; TrendRadar</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:2px;">
              AI, Finance &amp; Technology News</div>
          </td>
          <td align="right" style="vertical-align:middle;">
            <span style="background-color:#1e293b;color:#e2e8f0;font-size:10px;
              font-weight:700;padding:5px 10px;border-radius:20px;letter-spacing:0.5px;">
              {mode_label}</span>
          </td>
        </tr></table>
      </td>
    </tr>

    <!-- Stats bar -->
    <tr>
      <td style="background-color:#1e293b;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
          <td align="center" style="padding:10px 16px;border-right:1px solid #334155;">
            <div style="color:#94a3b8;font-size:9px;font-weight:700;
              letter-spacing:0.8px;text-transform:uppercase;">ITEMS</div>
            <div style="color:#f1f5f9;font-size:20px;font-weight:700;margin-top:1px;">
              {total_titles}</div>
          </td>
          <td align="center" style="padding:10px 16px;border-right:1px solid #334155;">
            <div style="color:#94a3b8;font-size:9px;font-weight:700;
              letter-spacing:0.8px;text-transform:uppercase;">CATEGORIES</div>
            <div style="color:#f1f5f9;font-size:20px;font-weight:700;margin-top:1px;">
              {total_categories}</div>
          </td>
          <td align="center" style="padding:10px 16px;">
            <div style="color:#94a3b8;font-size:9px;font-weight:700;
              letter-spacing:0.8px;text-transform:uppercase;">GENERATED</div>
            <div style="color:#f1f5f9;font-size:12px;font-weight:600;margin-top:3px;">
              {date_str}</div>
          </td>
        </tr></table>
      </td>
    </tr>

    <!-- Content -->
    <tr>
      <td class="content" style="padding:20px 20px 4px 20px;background-color:#f8fafc;">
"""
    ]

    active_stats = [s for s in stats if s.get("count", 0) > 0]
    for i in range(0, len(active_stats), 2):
        left = active_stats[i]
        right = active_stats[i + 1] if i + 1 < len(active_stats) else None

        html_parts.append(
            '<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr valign="top">'
        )
        html_parts.append(
            '<td class="col-l" width="49%" style="vertical-align:top;padding-right:8px;">'
        )
        html_parts.append(_render_email_category_card(left))
        html_parts.append("</td>")
        html_parts.append(
            '<td class="col-gap" width="2%" style="font-size:0;line-height:0;">&nbsp;</td>'
        )
        if right:
            html_parts.append(
                '<td class="col-r" width="49%" style="vertical-align:top;padding-left:8px;">'
            )
            html_parts.append(_render_email_category_card(right))
            html_parts.append("</td>")
        else:
            html_parts.append('<td width="49%"></td>')
        html_parts.append("</tr></table>")

    html_parts.append(
        """
      </td>
    </tr>

    <!-- Footer -->
    <tr>
      <td style="background-color:#0f172a;padding:14px 24px;text-align:center;">
        <p style="margin:0;color:#64748b;font-size:11px;">
          Generated by <strong style="color:#94a3b8;">TrendRadar</strong>
          &nbsp;&middot;&nbsp;
          <a href="https://github.com/sansan0/TrendRadar"
            style="color:#6366f1;text-decoration:none;">GitHub</a>
        </p>
      </td>
    </tr>

  </table>
</td></tr>
</table>
</body>
</html>"""
    )

    return "".join(html_parts)


def send_to_email(
    from_email: str,
    password: str,
    to_email: str,
    report_type: str,
    html_file_path: str,
    custom_smtp_server: Optional[str] = None,
    custom_smtp_port: Optional[int] = None,
    report_data: Optional[Dict] = None,
    mode: str = "daily",
) -> bool:
    """Send email notification"""
    try:
        if not html_file_path or not Path(html_file_path).exists():
            print(f"Error：HTML文件不存在或未提供: {html_file_path}")
            return False

        print(f"Using HTML file: {html_file_path}")
        with open(html_file_path, "r", encoding="utf-8") as f:
            original_html = f.read()

        html_content = convert_to_gmail_html(original_html, report_data, mode)

        domain = from_email.split("@")[-1].lower()

        if custom_smtp_server and custom_smtp_port:
            # Use custom SMTP configuration
            smtp_server = custom_smtp_server
            smtp_port = int(custom_smtp_port)
            # Determine encryption based on port: 465=SSL, 587=TLS
            if smtp_port == 465:
                use_tls = False  # SSL 模式（SMTP_SSL）
            elif smtp_port == 587:
                use_tls = True   # TLS 模式（STARTTLS）
            else:
                # For other ports, try TLS first (more secure, more widely supported)
                use_tls = True
        elif domain in SMTP_CONFIGS:
            # Use preset configuration
            config = SMTP_CONFIGS[domain]
            smtp_server = config["server"]
            smtp_port = config["port"]
            use_tls = config["encryption"] == "TLS"
        else:
            print(f"Unrecognized email service provider: {domain}, using generic SMTP configuration")
            smtp_server = f"smtp.{domain}"
            smtp_port = 587
            use_tls = True

        msg = MIMEMultipart("alternative")

        # Strictly set From header according to RFC standard
        sender_name = "TrendRadar"
        msg["From"] = formataddr((sender_name, from_email))

        # 设置收件人
        recipients = [addr.strip() for addr in to_email.split(",")]
        if len(recipients) == 1:
            msg["To"] = recipients[0]
        else:
            msg["To"] = ", ".join(recipients)

        # Set email subject with UTC time
        now_utc = datetime.now(pytz.UTC)
        now = get_utc_time()
        subject = f"TrendRadar Hot Topics Analysis Report - {report_type} - {now_utc.strftime('%m-%d %H:%M')} UTC"
        msg["Subject"] = Header(subject, "utf-8")

        # Set other standard headers
        msg["MIME-Version"] = "1.0"
        msg["Date"] = formatdate(localtime=False)
        msg["Message-ID"] = make_msgid()

        # 添加纯文本部分（作为备选）
        text_content = f"""
TrendRadar Hot Topics Analysis Report
========================
Report Type:{report_type}
Generated Time:{now.strftime('%Y-%m-%d %H:%M:%S')}

Please use an HTML-enabled email client to view the complete report.
        """
        text_part = MIMEText(text_content, "plain", "utf-8")
        msg.attach(text_part)

        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        print(f"Sending email to {to_email}...")
        print(f"SMTP server: {smtp_server}:{smtp_port}")
        print(f"Sender: {from_email}")

        try:
            if use_tls:
                # TLS 模式
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                server.set_debuglevel(0)  # 设为1可以查看详细调试信息
                server.ehlo()
                server.starttls()
                server.ehlo()
            else:
                # SSL 模式
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
                server.set_debuglevel(0)
                server.ehlo()

            # 登录
            server.login(from_email, password)

            # 发送邮件
            server.send_message(msg)
            server.quit()

            print(f"Email sent successfully [{report_type}] -> {to_email}")
            return True

        except smtplib.SMTPServerDisconnected:
            print(f"邮件发送Failed：服务器意外断开连接，请检查网络或稍后重试")
            return False

    except smtplib.SMTPAuthenticationError as e:
        print(f"邮件发送Failed：认证Error，请检查邮箱和密码/授权码")
        print(f"详细Error: {str(e)}")
        return False
    except smtplib.SMTPRecipientsRefused as e:
        print(f"邮件发送Failed：收件人地址被拒绝 {e}")
        return False
    except smtplib.SMTPSenderRefused as e:
        print(f"邮件发送Failed：发件人地址被拒绝 {e}")
        return False
    except smtplib.SMTPDataError as e:
        print(f"邮件发送Failed：邮件数据Error {e}")
        return False
    except smtplib.SMTPConnectError as e:
        print(f"邮件发送Failed：无法连接到 SMTP 服务器 {smtp_server}:{smtp_port}")
        print(f"详细Error: {str(e)}")
        return False
    except Exception as e:
        print(f"邮件发送Failed [{report_type}]：{e}")
        import traceback

        traceback.print_exc()
        return False


def send_to_ntfy(
    server_url: str,
    topic: str,
    token: Optional[str],
    report_data: Dict,
    report_type: str,
    update_info: Optional[Dict] = None,
    proxy_url: Optional[str] = None,
    mode: str = "daily",
) -> bool:
    """Send to ntfy (supports batch sending, strictly adheres to 4KB limit)"""
    # Avoid HTTP header encoding issues
    report_type_en_map = {
        "Daily Summary": "Daily Summary",
        "当前榜单汇总": "Current Ranking",
        "Incremental Update": "Incremental Update",
        "实时增量": "Realtime Incremental", 
        "实时当前榜单": "Realtime Current Ranking",  
    }
    report_type_en = report_type_en_map.get(report_type, "News Report") 

    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Markdown": "yes",
        "Title": report_type_en,
        "Priority": "default",
        "Tags": "news",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    # Build complete URL, ensure correct format
    base_url = server_url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"
    url = f"{base_url}/{topic}"

    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    # 获取分批内容，使用ntfy专用的4KB限制
    batches = split_content_into_batches(
        report_data, "ntfy", update_info, max_bytes=3800, mode=mode
    )

    total_batches = len(batches)
    print(f"ntfy message divided into {total_batches} 批times发送 [{report_type}]")

    # 反转批times顺序，使得在ntfy客户端显示时顺序正确
    # ntfy显示最新消息在上面，所以我们从最后一批开始推送
    reversed_batches = list(reversed(batches))
    
    print(f"ntfy将按反向顺序推送（最后批times先推送），确保客户端显示顺序正确")

    # 逐批发送（反向顺序）
    success_count = 0
    for idx, batch_content in enumerate(reversed_batches, 1):
        # 计算正确的批times编号（用户视角的编号）
        actual_batch_num = total_batches - idx + 1
        
        batch_size = len(batch_content.encode("utf-8"))
        print(
            f"发送ntfyBatch {actual_batch_num}/{total_batches} 批times（推送顺序: {idx}/{total_batches}），大小：{batch_size} 字节 [{report_type}]"
        )

        # 检查消息大小，确保不超过4KB
        if batch_size > 4096:
            print(f"Warning：ntfyBatch {actual_batch_num} 批times消息过大（{batch_size} bytes), may be rejected")

        # 添加批times标识（使用正确的批times编号）
        current_headers = headers.copy()
        if total_batches > 1:
            batch_header = f"**[Batch {actual_batch_num}/{total_batches} 批times]**\n\n"
            batch_content = batch_header + batch_content
            current_headers["Title"] = (
                f"{report_type_en} ({actual_batch_num}/{total_batches})"
            )

        try:
            response = requests.post(
                url,
                headers=current_headers,
                data=batch_content.encode("utf-8"),
                proxies=proxies,
                timeout=30,
            )

            if response.status_code == 200:
                print(f"ntfyBatch {actual_batch_num}/{total_batches} 批times发送Success [{report_type}]")
                success_count += 1
                if idx < total_batches:
                    # 公共服务器建议 2-3 秒，自托管可以更短
                    interval = 2 if "ntfy.sh" in server_url else 1
                    time.sleep(interval)
            elif response.status_code == 429:
                print(
                    f"ntfyBatch {actual_batch_num}/{total_batches} 批times速率限制 [{report_type}]，等待后重试"
                )
                time.sleep(10)  # 等待10秒后重试
                # 重试一times
                retry_response = requests.post(
                    url,
                    headers=current_headers,
                    data=batch_content.encode("utf-8"),
                    proxies=proxies,
                    timeout=30,
                )
                if retry_response.status_code == 200:
                    print(f"ntfyBatch {actual_batch_num}/{total_batches} 批times重试Success [{report_type}]")
                    success_count += 1
                else:
                    print(
                        f"ntfyBatch {actual_batch_num}/{total_batches} 批times重试Failed，状态码：{retry_response.status_code}"
                    )
            elif response.status_code == 413:
                print(
                    f"ntfyBatch {actual_batch_num}/{total_batches} 批times消息过大被拒绝 [{report_type}]，消息大小：{batch_size} 字节"
                )
            else:
                print(
                    f"ntfyBatch {actual_batch_num}/{total_batches} 批times发送Failed [{report_type}]，状态码：{response.status_code}"
                )
                try:
                    print(f"Error详情：{response.text}")
                except:
                    pass

        except requests.exceptions.ConnectTimeout:
            print(f"ntfyBatch {actual_batch_num}/{total_batches} 批times连接超时 [{report_type}]")
        except requests.exceptions.ReadTimeout:
            print(f"ntfyBatch {actual_batch_num}/{total_batches} 批times读取超时 [{report_type}]")
        except requests.exceptions.ConnectionError as e:
            print(f"ntfyBatch {actual_batch_num}/{total_batches} 批times连接Error [{report_type}]：{e}")
        except Exception as e:
            print(f"ntfyBatch {actual_batch_num}/{total_batches} 批times发送异常 [{report_type}]：{e}")

    # 判断整体发送是否Success
    if success_count == total_batches:
        print(f"ntfyAll {total_batches} 批times发送完成 [{report_type}]")
        return True
    elif success_count > 0:
        print(f"ntfy部分发送Success：{success_count}/{total_batches} 批times [{report_type}]")
        return True  # 部分Success也视为Success
    else:
        print(f"ntfy发送完全Failed [{report_type}]")
        return False


# === 主分析器 ===
class NewsAnalyzer:
    """News analyzer"""

    # Mode strategy definitions
    MODE_STRATEGIES = {
        "incremental": {
            "mode_name": "Incremental Mode",
            "description": "Incremental Mode (Only new matching news, no push if no new items)",
            "realtime_report_type": "Incremental Update",
            "summary_report_type": "Daily Summary",
            "should_send_realtime": True,
            "should_generate_summary": True,
            "summary_mode": "daily",
        },
        "current": {
            "mode_name": "Current Rankings Mode",
            "description": "Current Rankings Mode (Current rankings + new items section + scheduled push)",
            "realtime_report_type": "Current Rankings",
            "summary_report_type": "Rankings Summary",
            "should_send_realtime": True,
            "should_generate_summary": True,
            "summary_mode": "current",
        },
        "daily": {
            "mode_name": "Daily Summary Mode",
            "description": "Daily Summary Mode (All matching news + new items section + scheduled push)",
            "realtime_report_type": "",
            "summary_report_type": "Daily Summary",
            "should_send_realtime": False,
            "should_generate_summary": True,
            "summary_mode": "daily",
        },
    }

    def __init__(self):
        self.request_interval = CONFIG["REQUEST_INTERVAL"]
        self.report_mode = CONFIG["REPORT_MODE"]
        self.rank_threshold = CONFIG["RANK_THRESHOLD"]
        self.is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
        self.is_docker_container = self._detect_docker_environment()
        self.update_info = None
        self.proxy_url = None
        self._setup_proxy()

        # Get News API key from config (env var takes priority)
        newsapi_key = CONFIG.get('NEWSAPI_KEY', '')
        self.data_fetcher = DataFetcher(self.proxy_url, newsapi_key)

        if self.is_github_actions:
            self._check_version_update()
            
        self.dedup_manager = DeduplicationManager(retention_hours=72)

    def _detect_docker_environment(self) -> bool:
        """Detect if running in Docker container"""
        try:
            if os.environ.get("DOCKER_CONTAINER") == "true":
                return True

            if os.path.exists("/.dockerenv"):
                return True

            return False
        except Exception:
            return False

    def _should_open_browser(self) -> bool:
        """Determine if browser should be opened"""
        return not self.is_github_actions and not self.is_docker_container

    def _setup_proxy(self) -> None:
        """Set proxy configuration"""
        if not self.is_github_actions and CONFIG["USE_PROXY"]:
            self.proxy_url = CONFIG["DEFAULT_PROXY"]
            print("本地环境，使用代理")
        elif not self.is_github_actions and not CONFIG["USE_PROXY"]:
            print("本地环境，未启用代理")
        else:
            print("GitHub Actions environment, proxy disabled")

    def _check_version_update(self) -> None:
        """Check for version updates"""
        try:
            need_update, remote_version = check_version_update(
                VERSION, CONFIG["VERSION_CHECK_URL"], self.proxy_url
            )

            if need_update and remote_version:
                self.update_info = {
                    "current_version": VERSION,
                    "remote_version": remote_version,
                }
                print(f"发现新版本: {remote_version} (当前: {VERSION})")
            else:
                print("版本检查完成，当前为最新版本")
        except Exception as e:
            print(f"版本检查出错: {e}")

    def _get_mode_strategy(self) -> Dict:
        """Get strategy configuration for current mode"""
        return self.MODE_STRATEGIES.get(self.report_mode, self.MODE_STRATEGIES["daily"])

    def _has_notification_configured(self) -> bool:
        """Check if any notification channels are configured"""
        return any(
            [
                CONFIG["FEISHU_WEBHOOK_URL"],
                CONFIG["DINGTALK_WEBHOOK_URL"],
                CONFIG["WEWORK_WEBHOOK_URL"],
                (CONFIG["TELEGRAM_BOT_TOKEN"] and CONFIG["TELEGRAM_CHAT_ID"]),
                (
                    CONFIG["EMAIL_FROM"]
                    and CONFIG["EMAIL_PASSWORD"]
                    and CONFIG["EMAIL_TO"]
                ),
                (CONFIG["NTFY_SERVER_URL"] and CONFIG["NTFY_TOPIC"]),
            ]
        )

    def _has_valid_content(
        self, stats: List[Dict], new_titles: Optional[Dict] = None
    ) -> bool:
        """Check if there is valid news content"""
        if self.report_mode in ["incremental", "current"]:
            # 增量模式和current模式下，只要stats有内容就说明有匹配的新闻
            return any(stat["count"] > 0 for stat in stats)
        else:
            # Daily Summary模式下，检查是否有匹配的频率词新闻或New新闻
            has_matched_news = any(stat["count"] > 0 for stat in stats)
            has_new_news = bool(
                new_titles and any(len(titles) > 0 for titles in new_titles.values())
            )
            return has_matched_news or has_new_news

    def _load_analysis_data(
        self,
        precomputed_new_titles: Optional[Dict] = None,
    ) -> Optional[Tuple[Dict, Dict, Dict, Dict, List, List]]:
        """Unified data loading and preprocessing, filtering historical data using current monitored platform list"""
        try:
            # Get currently configured monitored platform ID list
            current_platform_ids = []
            for platform in CONFIG["PLATFORMS"]:
                current_platform_ids.append(platform["id"])

            print(f"Current monitored platforms: {current_platform_ids}")

            all_results, id_to_name, title_info = read_all_today_titles(
                current_platform_ids
            )

            if not all_results:
                print("没有找到当天的数据")
                return None

            total_titles = sum(len(titles) for titles in all_results.values())
            print(f"Read {total_titles} news items (filtered by current monitored platforms)")

            if precomputed_new_titles is not None:
                new_titles = precomputed_new_titles
            else:
                new_titles = detect_latest_new_titles(current_platform_ids, self.dedup_manager)
            word_groups, filter_words = load_frequency_words()

            return (
                all_results,
                id_to_name,
                title_info,
                new_titles,
                word_groups,
                filter_words,
            )
        except Exception as e:
            print(f"数据加载Failed: {e}")
            return None

    def _prepare_current_title_info(self, results: Dict, time_info: str) -> Dict:
        """从当前抓取结果构建Title信息"""
        title_info = {}
        for source_id, titles_data in results.items():
            title_info[source_id] = {}
            for title, title_data in titles_data.items():
                ranks = title_data.get("ranks", [])
                url = title_data.get("url", "")
                mobile_url = title_data.get("mobileUrl", "")

                title_info[source_id][title] = {
                    "first_time": time_info,
                    "last_time": time_info,
                    "count": 1,
                    "ranks": ranks,
                    "url": url,
                    "mobileUrl": mobile_url,
                }
        return title_info

    def _run_analysis_pipeline(
        self,
        data_source: Dict,
        mode: str,
        title_info: Dict,
        new_titles: Dict,
        word_groups: List[Dict],
        filter_words: List[str],
        id_to_name: Dict,
        failed_ids: Optional[List] = None,
        is_daily_summary: bool = False,
    ) -> Tuple[List[Dict], str]:
        """Unified analysis pipeline: Data processing -> Statistical calculation -> HTML generation"""

        # Statistical calculation
        stats, total_titles = count_word_frequency(
            data_source,
            word_groups,
            filter_words,
            id_to_name,
            title_info,
            self.rank_threshold,
            new_titles,
            mode=mode,
        )

        # HTML generation
        html_file = generate_html_report(
            stats,
            total_titles,
            failed_ids=failed_ids,
            new_titles=new_titles,
            id_to_name=id_to_name,
            mode=mode,
            is_daily_summary=is_daily_summary,
            update_info=self.update_info if CONFIG["SHOW_VERSION_UPDATE"] else None,
        )

        return stats, html_file

    def _send_notification_if_needed(
        self,
        stats: List[Dict],
        report_type: str,
        mode: str,
        failed_ids: Optional[List] = None,
        new_titles: Optional[Dict] = None,
        id_to_name: Optional[Dict] = None,
        html_file_path: Optional[str] = None,
    ) -> bool:
        """Unified notification sending logic, including all judgment conditions"""
        has_notification = self._has_notification_configured()

        if (
            CONFIG["ENABLE_NOTIFICATION"]
            and has_notification
            and self._has_valid_content(stats, new_titles)
        ):
            send_to_notifications(
                stats,
                failed_ids or [],
                report_type,
                new_titles,
                id_to_name,
                self.update_info,
                self.proxy_url,
                mode=mode,
                html_file_path=html_file_path,
            )
            return True
        elif CONFIG["ENABLE_NOTIFICATION"] and not has_notification:
            print("⚠️ Warning：通知功能已启用但未配置任何通知渠道，将跳过通知发送")
        elif not CONFIG["ENABLE_NOTIFICATION"]:
            print(f"跳过{report_type}通知：通知功能已禁用")
        elif (
            CONFIG["ENABLE_NOTIFICATION"]
            and has_notification
            and not self._has_valid_content(stats, new_titles)
        ):
            mode_strategy = self._get_mode_strategy()
            if "实时" in report_type:
                print(
                    f"跳过实时推送通知：{mode_strategy['mode_name']}下未检测到匹配的新闻"
                )
            else:
                print(
                    f"跳过{mode_strategy['summary_report_type']}通知：未匹配到有效的新闻内容"
                )

        return False

    def _generate_summary_report(self, mode_strategy: Dict, precomputed_new_titles: Optional[Dict] = None) -> Optional[str]:
        """Generate summary report (with notification)"""
        summary_type = (
            "当前榜单汇总" if mode_strategy["summary_mode"] == "current" else "Daily Summary"
        )
        print(f"生成{summary_type}报告...")

        # For daily summaries, enforce a 23h cooldown independent of push window settings.
        # This prevents duplicate emails when UTC midnight rolls over the calendar day.
        summary_push_manager = PushRecordManager()
        if mode_strategy["summary_mode"] == "daily" and summary_push_manager.has_pushed_recently(cooldown_hours=23):
            print("Daily summary: last notification was sent within 23h — generating HTML only, skipping notification")
            return self._generate_summary_html(mode_strategy["summary_mode"])

        # 加载分析数据
        analysis_data = self._load_analysis_data(precomputed_new_titles=precomputed_new_titles)
        if not analysis_data:
            return None

        all_results, id_to_name, title_info, new_titles, word_groups, filter_words = (
            analysis_data
        )

        # 运行分析流水线
        stats, html_file = self._run_analysis_pipeline(
            all_results,
            mode_strategy["summary_mode"],
            title_info,
            new_titles,
            word_groups,
            filter_words,
            id_to_name,
            is_daily_summary=True,
        )

        print(f"{summary_type}报告已生成: {html_file}")

        # 发送通知并记录推送时间（供23h冷却检查使用）
        sent = self._send_notification_if_needed(
            stats,
            mode_strategy["summary_report_type"],
            mode_strategy["summary_mode"],
            failed_ids=[],
            new_titles=new_titles,
            id_to_name=id_to_name,
            html_file_path=html_file,
        )
        if sent and mode_strategy["summary_mode"] == "daily":
            summary_push_manager.record_push(mode_strategy["summary_report_type"])

        return html_file

    def _generate_summary_html(self, mode: str = "daily") -> Optional[str]:
        """Generate summary HTML"""
        summary_type = "当前榜单汇总" if mode == "current" else "Daily Summary"
        print(f"生成{summary_type}HTML...")

        # 加载分析数据
        analysis_data = self._load_analysis_data()
        if not analysis_data:
            return None

        all_results, id_to_name, title_info, new_titles, word_groups, filter_words = (
            analysis_data
        )

        # 运行分析流水线
        _, html_file = self._run_analysis_pipeline(
            all_results,
            mode,
            title_info,
            new_titles,
            word_groups,
            filter_words,
            id_to_name,
            is_daily_summary=True,
        )

        print(f"{summary_type}HTML已生成: {html_file}")
        return html_file

    def _initialize_and_check_config(self) -> None:
        """General initialization and configuration check"""
        now = get_utc_time()
        print(f"Current UTC time: {datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC")

        if not CONFIG["ENABLE_CRAWLER"]:
            print("爬虫功能已禁用（ENABLE_CRAWLER=False），程序退出")
            return

        has_notification = self._has_notification_configured()
        if not CONFIG["ENABLE_NOTIFICATION"]:
            print("Notification disabled (ENABLE_NOTIFICATION=False), will only crawl data")
        elif not has_notification:
            print("No notification channels configured, will only crawl data without sending notifications")
        else:
            print("Notification enabled, will send notifications")

        mode_strategy = self._get_mode_strategy()
        print(f"Report mode: {self.report_mode}")
        print(f"Operation mode: {mode_strategy['description']}")

    def _crawl_data(self) -> Tuple[Dict, Dict, List, str]:
        """Execute data crawling"""
        platforms = CONFIG["PLATFORMS"]

        print(
            f"Configured platforms: {[p.get('name', p['id']) for p in platforms]}"
        )
        print(f"Starting data crawl, request interval: {self.request_interval}ms")
        ensure_directory_exists("output")

        results, id_to_name, failed_ids = self.data_fetcher.crawl_websites(
            platforms, self.request_interval
        )

        title_file = save_titles_to_file(results, id_to_name, failed_ids)
        print(f"News saved to: {title_file}")

        return results, id_to_name, failed_ids, title_file

    def _execute_mode_strategy(
        self, mode_strategy: Dict, results: Dict, id_to_name: Dict, failed_ids: List, title_file: str
    ) -> Optional[str]:
        """Execute mode-specific logic"""
        # Get current monitored platform ID list
        current_platform_ids = [platform["id"] for platform in CONFIG["PLATFORMS"]]

        new_titles = detect_latest_new_titles(current_platform_ids, self.dedup_manager)
        time_info = Path(title_file).stem
        word_groups, filter_words = load_frequency_words()

        # current模式下，实时推送需要使用完整的历史数据来保证统计信息的完整性
        if self.report_mode == "current":
            # 加载完整的历史数据（已按当前平台过滤）
            analysis_data = self._load_analysis_data()
            if analysis_data:
                (
                    all_results,
                    historical_id_to_name,
                    historical_title_info,
                    historical_new_titles,
                    _,
                    _,
                ) = analysis_data

                print(
                    f"current模式：使用过滤后的历史数据，包含平台：{list(all_results.keys())}"
                )

                stats, html_file = self._run_analysis_pipeline(
                    all_results,
                    self.report_mode,
                    historical_title_info,
                    historical_new_titles,
                    word_groups,
                    filter_words,
                    historical_id_to_name,
                    failed_ids=failed_ids,
                )

                combined_id_to_name = {**historical_id_to_name, **id_to_name}

                print(f"HTML report generated: {html_file}")

                # 发送实时通知（使用完整历史数据的统计结果）
                summary_html = None
                if mode_strategy["should_send_realtime"]:
                    self._send_notification_if_needed(
                        stats,
                        mode_strategy["realtime_report_type"],
                        self.report_mode,
                        failed_ids=failed_ids,
                        new_titles=historical_new_titles,
                        id_to_name=combined_id_to_name,
                        html_file_path=html_file,
                    )
            else:
                print("❌ 严重Error：无法读取刚保存的数据文件")
                raise RuntimeError("数据一致性检查Failed：保存后立即读取Failed")
        else:
            title_info = self._prepare_current_title_info(results, time_info)
            stats, html_file = self._run_analysis_pipeline(
                results,
                self.report_mode,
                title_info,
                new_titles,
                word_groups,
                filter_words,
                id_to_name,
                failed_ids=failed_ids,
            )
            print(f"HTML报告已生成: {html_file}")

            # 发送实时通知（如果需要）
            summary_html = None
            if mode_strategy["should_send_realtime"]:
                self._send_notification_if_needed(
                    stats,
                    mode_strategy["realtime_report_type"],
                    self.report_mode,
                    failed_ids=failed_ids,
                    new_titles=new_titles,
                    id_to_name=id_to_name,
                    html_file_path=html_file,
                )

        # 生成汇总报告（如果需要）
        summary_html = None
        if mode_strategy["should_generate_summary"]:
            if mode_strategy["should_send_realtime"]:
                # 如果已经发送了实时通知，汇总只生成HTML不发送通知
                summary_html = self._generate_summary_html(
                    mode_strategy["summary_mode"]
                )
            else:
                # daily模式：直接生成汇总报告并发送通知，传入已计算的new_titles避免二次检测
                summary_html = self._generate_summary_report(mode_strategy, precomputed_new_titles=new_titles)

        # 打开浏览器（仅在非容器环境）
        if self._should_open_browser() and html_file:
            if summary_html:
                summary_url = "file://" + str(Path(summary_html).resolve())
                print(f"正在打开汇总报告: {summary_url}")
                webbrowser.open(summary_url)
            else:
                file_url = "file://" + str(Path(html_file).resolve())
                print(f"正在打开HTML报告: {file_url}")
                webbrowser.open(file_url)
        elif self.is_docker_container and html_file:
            if summary_html:
                print(f"汇总报告已生成（Docker环境）: {summary_html}")
            else:
                print(f"HTML报告已生成（Docker环境）: {html_file}")

        return summary_html

    def run(self) -> None:
        """Execute analysis process"""
        try:
            self._initialize_and_check_config()

            mode_strategy = self._get_mode_strategy()

            results, id_to_name, failed_ids, title_file = self._crawl_data()

            self._execute_mode_strategy(mode_strategy, results, id_to_name, failed_ids, title_file)
            
            # Save deduplication state
            if self.dedup_manager:
                self.dedup_manager.save()

        except Exception as e:
            print(f"分析流程执行出错: {e}")
            raise


def main():
    try:
        analyzer = NewsAnalyzer()
        analyzer.run()
    except FileNotFoundError as e:
        print(f"❌ 配置文件Error: {e}")
        print("\n请确保以下文件存在:")
        print("  • config/config.yaml")
        print("  • config/frequency_words.txt")
        print("\n参考项目文档进行正确配置")
    except Exception as e:
        print(f"❌ 程序运行Error: {e}")
        raise


if __name__ == "__main__":
    main()
