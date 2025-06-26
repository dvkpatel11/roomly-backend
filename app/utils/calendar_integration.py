from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from dataclasses import dataclass


@dataclass
class CalendarEvent:
    title: str
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    event_id: Optional[str] = None


class GoogleCalendarIntegration:
    """Google Calendar integration utility"""

    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self.base_url = "https://www.googleapis.com/calendar/v3"
        self.access_token = None

    def authenticate(self, auth_code: str) -> bool:
        """Authenticate with Google Calendar using OAuth2"""
        try:
            # Exchange auth code for access token
            token_url = "https://oauth2.googleapis.com/token"

            data = {
                "client_id": self.credentials.get("client_id"),
                "client_secret": self.credentials.get("client_secret"),
                "code": auth_code,
                "grant_type": "authorization_code",
                "redirect_uri": self.credentials.get("redirect_uri"),
            }

            response = requests.post(token_url, data=data)

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                return True

            return False
        except Exception:
            return False

    def get_events(self, days_ahead: int = 7) -> List[CalendarEvent]:
        """Get events from Google Calendar"""
        if not self.access_token:
            return []

        try:
            now = datetime.utcnow()
            future_date = now + timedelta(days=days_ahead)

            url = f"{self.base_url}/calendars/primary/events"
            headers = {"Authorization": f"Bearer {self.access_token}"}

            params = {
                "timeMin": now.isoformat() + "Z",
                "timeMax": future_date.isoformat() + "Z",
                "singleEvents": True,
                "orderBy": "startTime",
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                events_data = response.json()
                events = []

                for item in events_data.get("items", []):
                    start = item["start"].get("dateTime", item["start"].get("date"))
                    end = item["end"].get("dateTime", item["end"].get("date"))

                    # Parse datetime
                    start_time = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    end_time = datetime.fromisoformat(end.replace("Z", "+00:00"))

                    event = CalendarEvent(
                        title=item.get("summary", "No Title"),
                        start_time=start_time,
                        end_time=end_time,
                        description=item.get("description"),
                        location=item.get("location"),
                        event_id=item.get("id"),
                    )

                    events.append(event)

                return events

            return []
        except Exception:
            return []

    def create_event(self, event: CalendarEvent) -> Optional[str]:
        """Create event in Google Calendar"""
        if not self.access_token:
            return None

        try:
            url = f"{self.base_url}/calendars/primary/events"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            event_data = {
                "summary": event.title,
                "description": event.description,
                "location": event.location,
                "start": {"dateTime": event.start_time.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": event.end_time.isoformat(), "timeZone": "UTC"},
            }

            response = requests.post(url, headers=headers, json=event_data)

            if response.status_code == 200:
                created_event = response.json()
                return created_event.get("id")

            return None
        except Exception:
            return None

    def check_conflicts(
        self, start_time: datetime, end_time: datetime
    ) -> List[CalendarEvent]:
        """Check for calendar conflicts in given time range"""
        events = self.get_events(30)  # Check next 30 days

        conflicts = []
        for event in events:
            # Check if events overlap
            if start_time < event.end_time and end_time > event.start_time:
                conflicts.append(event)

        return conflicts


class AppleCalendarIntegration:
    """Apple Calendar integration utility (simplified)"""

    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        # Apple Calendar would use CalDAV protocol
        self.caldav_url = credentials.get("caldav_url")
        self.username = credentials.get("username")
        self.password = credentials.get("password")

    def get_events(self, days_ahead: int = 7) -> List[CalendarEvent]:
        """Get events from Apple Calendar via CalDAV"""
        # This would require a CalDAV library like caldav
        # For now, return empty list as placeholder
        return []

    def create_event(self, event: CalendarEvent) -> Optional[str]:
        """Create event in Apple Calendar via CalDAV"""
        # This would use CalDAV protocol
        return None

    def check_conflicts(
        self, start_time: datetime, end_time: datetime
    ) -> List[CalendarEvent]:
        """Check for calendar conflicts"""
        return []


class CalendarService:
    """Unified calendar service for multiple providers"""

    def __init__(self):
        self.google_integration = None
        self.apple_integration = None

    def setup_google_calendar(self, credentials: Dict[str, str]) -> bool:
        """Setup Google Calendar integration"""
        try:
            self.google_integration = GoogleCalendarIntegration(credentials)
            return True
        except Exception:
            return False

    def setup_apple_calendar(self, credentials: Dict[str, str]) -> bool:
        """Setup Apple Calendar integration"""
        try:
            self.apple_integration = AppleCalendarIntegration(credentials)
            return True
        except Exception:
            return False

    def get_all_events(self, days_ahead: int = 7) -> Dict[str, List[CalendarEvent]]:
        """Get events from all connected calendars"""
        events = {"google": [], "apple": []}

        if self.google_integration:
            events["google"] = self.google_integration.get_events(days_ahead)

        if self.apple_integration:
            events["apple"] = self.apple_integration.get_events(days_ahead)

        return events

    def check_all_conflicts(
        self, start_time: datetime, end_time: datetime
    ) -> Dict[str, List[CalendarEvent]]:
        """Check conflicts across all connected calendars"""
        conflicts = {"google": [], "apple": []}

        if self.google_integration:
            conflicts["google"] = self.google_integration.check_conflicts(
                start_time, end_time
            )

        if self.apple_integration:
            conflicts["apple"] = self.apple_integration.check_conflicts(
                start_time, end_time
            )

        return conflicts

    def create_event_in_calendar(
        self, event: CalendarEvent, provider: str = "google"
    ) -> Optional[str]:
        """Create event in specified calendar provider"""

        if provider == "google" and self.google_integration:
            return self.google_integration.create_event(event)
        elif provider == "apple" and self.apple_integration:
            return self.apple_integration.create_event(event)

        return None

    def sync_roomly_event_to_calendar(
        self, roomly_event: Dict[str, Any], provider: str = "google"
    ) -> Optional[str]:
        """Sync a Roomly event to external calendar"""

        calendar_event = CalendarEvent(
            title=f"🏠 {roomly_event['title']}",
            start_time=roomly_event["start_date"],
            end_time=roomly_event["end_date"]
            or roomly_event["start_date"] + timedelta(hours=2),
            description=f"Roomly Event: {roomly_event.get('description', '')}\n\nEvent Type: {roomly_event['event_type']}",
            location=roomly_event.get("location"),
        )

        return self.create_event_in_calendar(calendar_event, provider)

    def get_user_availability(
        self, user_id: int, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Check user availability across all calendars"""

        conflicts = self.check_all_conflicts(start_time, end_time)

        total_conflicts = len(conflicts["google"]) + len(conflicts["apple"])

        return {
            "is_available": total_conflicts == 0,
            "conflict_count": total_conflicts,
            "conflicts": conflicts,
            "availability_score": max(
                0, 100 - (total_conflicts * 25)
            ),  # Reduce score by 25 per conflict
        }


# Utility functions for calendar integration
def format_calendar_event_for_roomly(calendar_event: CalendarEvent) -> Dict[str, Any]:
    """Convert calendar event to Roomly-compatible format"""
    return {
        "title": calendar_event.title,
        "start_date": calendar_event.start_time,
        "end_date": calendar_event.end_time,
        "description": calendar_event.description,
        "location": calendar_event.location,
        "external_event_id": calendar_event.event_id,
        "source": "external_calendar",
    }


def get_calendar_oauth_url(provider: str, credentials: Dict[str, str]) -> str:
    """Generate OAuth URL for calendar provider"""

    if provider == "google":
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": credentials.get("client_id"),
            "redirect_uri": credentials.get("redirect_uri"),
            "scope": "https://www.googleapis.com/auth/calendar",
            "response_type": "code",
            "access_type": "offline",
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query_string}"

    # Apple Calendar would use different OAuth flow
    return ""
