# Roomly API Endpoints

Generated on: $(date)

## Endpoint Summary


| Method | Endpoint | Router |
|--------|----------|--------|
| POST | `/login` | auth |
| GET | `/me` | auth |
| POST | `/logout` | auth |
| POST | `/refresh-token` | auth |
| POST | `/change-password` | auth |
| GET | `/profile` | auth |
| POST | `/` | bills |
| GET | `/` | bills |
| GET | `/upcoming` | bills |
| GET | `/overdue` | bills |
| GET | `/{bill_id}` | bills |
| PUT | `/{bill_id}` | bills |
| DELETE | `/{bill_id}` | bills |
| POST | `/{bill_id}/payments` | bills |
| GET | `/{bill_id}/payment-history` | bills |
| GET | `/summary` | bills |
| GET | `/config/categories` | bills |
| GET | `/config/split-methods` | bills |
| GET | `/announcements` | communications |
| GET | `/announcements/{announcement_id}` | communications |
| PUT | `/announcements/{announcement_id}` | communications |
| PUT | `/announcements/{announcement_id}/pin` | communications |
| GET | `/polls` | communications |
| GET | `/polls/{poll_id}` | communications |
| PUT | `/polls/{poll_id}` | communications |
| DELETE | `/polls/{poll_id}` | communications |
| POST | `/polls/{poll_id}/vote` | communications |
| PUT | `/polls/{poll_id}/close` | communications |
| GET | `/house-rules` | communications |
| PUT | `/house-rules` | communications |
| GET | `/summary` | communications |
| GET | `/config/categories` | communications |
| GET | `/config/priorities` | communications |
| GET | `/` | dashboard |
| GET | `/mobile` | dashboard |
| GET | `/quick-stats` | dashboard |
| GET | `/urgent-items` | dashboard |
| GET | `/financial-snapshot` | dashboard |
| GET | `/task-progress` | dashboard |
| GET | `/upcoming-events` | dashboard |
| GET | `/recent-activity` | dashboard |
| GET | `/quick-actions` | dashboard |
| GET | `/household-pulse` | dashboard |
| GET | `/notifications-summary` | dashboard |
| POST | `/refresh` | dashboard |
| GET | `/config/widgets` | dashboard |
| GET | `/config/layouts` | dashboard |
| GET | `/health-check` | dashboard |
| POST | `/` | event |
| GET | `/events` | event |
| GET | `/events/pending-approval` | event |
| PUT | `/events/{event_id}/approve` | event |
| PUT | `/events/{event_id}/deny` | event |
| PUT | `/events/{event_id}/cancel` | event |
| POST | `/events/{event_id}/rsvp` | event |
| GET | `/events/{event_id}/rsvps` | event |
| GET | `/my-events` | event |
| POST | `/check-conflicts` | event |
| POST | `/suggest-times` | event |
| GET | `/schedule-overview` | event |
| GET | `/statistics` | event |
| POST | `/` | expenses |
| GET | `/` | expenses |
| GET | `/{expense_id}` | expenses |
| PUT | `/{expense_id}` | expenses |
| DELETE | `/{expense_id}` | expenses |
| POST | `/{expense_id}/payments` | expenses |
| PUT | `/{expense_id}/split/{user_id}/mark-paid` | expenses |
| GET | `/me/summary` | expenses |
| GET | `/me/payment-history` | expenses |
| POST | `/preview-split` | expenses |
| GET | `/config/categories` | expenses |
| GET | `/config/split-methods` | expenses |
| GET | `/statistics/household` | expenses |
| POST | `/` | guests |
| GET | `/` | guests |
| GET | `/pending` | guests |
| GET | `/{guest_id}` | guests |
| PUT | `/{guest_id}/approve` | guests |
| PUT | `/{guest_id}/deny` | guests |
| DELETE | `/{guest_id}` | guests |
| GET | `/policies` | guests |
| PUT | `/policies` | guests |
| GET | `/calendar` | guests |
| GET | `/statistics` | guests |
| GET | `/config/relationship-types` | guests |
| POST | `/` | households |
| GET | `/me` | households |
| GET | `/{household_id}` | households |
| PUT | `/me` | households |
| GET | `/me/members` | households |
| POST | `/me/members` | households |
| DELETE | `/me/members/{user_id}` | households |
| PUT | `/me/members/{user_id}/role` | households |
| GET | `/me/health-score` | households |
| GET | `/me/statistics` | households |
| POST | `/me/invite` | households |
| POST | `/join` | households |
| POST | `/me/leave` | households |
| POST | `/me/transfer-ownership` | households |
| GET | `/config/roles` | households |
| GET | `/me/summary` | households |
| GET | `/` | notifications |
| GET | `/{notification_id}` | notifications |
| PUT | `/{notification_id}/read` | notifications |
| PUT | `/mark-all-read` | notifications |
| DELETE | `/{notification_id}` | notifications |
| GET | `/preferences` | notifications |
| PUT | `/preferences` | notifications |
| GET | `/unread-count` | notifications |
| GET | `/summary` | notifications |
| POST | `/system/trigger/bill-reminders` | notifications |
| POST | `/system/trigger/task-reminders` | notifications |
| POST | `/system/trigger/event-reminders` | notifications |
| POST | `/system/trigger/all-reminders` | notifications |
| GET | `/system/scheduler-status` | notifications |
| GET | `/config/types` | notifications |
| GET | `/config/priorities` | notifications |
| GET | `/lists` | shopping |
| GET | `/lists/{list_id}` | shopping |
| PUT | `/lists/{list_id}` | shopping |
| DELETE | `/lists/{list_id}` | shopping |
| PUT | `/lists/{list_id}/items/{item_id}` | shopping |
| PUT | `/lists/{list_id}/items/{item_id}/purchased` | shopping |
| PUT | `/lists/{list_id}/complete` | shopping |
| PUT | `/lists/{list_id}/reassign` | shopping |
| GET | `/lists/{list_id}/items` | shopping |
| GET | `/statistics` | shopping |
| GET | `/me/assignments` | shopping |
| GET | `/config/categories` | shopping |
| GET | `/templates` | shopping |
| POST | `/` | tasks |
| GET | `/` | tasks |
| GET | `/me` | tasks |
| GET | `/{task_id}` | tasks |
| PUT | `/{task_id}` | tasks |
| DELETE | `/{task_id}` | tasks |
| PUT | `/{task_id}/complete` | tasks |
| PUT | `/{task_id}/status` | tasks |
| PUT | `/{task_id}/reassign` | tasks |
| GET | `/leaderboard/current` | tasks |
| GET | `/me/score` | tasks |
| GET | `/rotation/schedule` | tasks |
| GET | `/overdue` | tasks |
| GET | `/config/priorities` | tasks |
| GET | `/config/statuses` | tasks |
| POST | `/bulk/reassign` | tasks |
| GET | `/statistics/household` | tasks |

## Detailed Endpoint Information

#### Detailed auth Endpoints

**POST** `/logout`
- Function: logout

#### Detailed bills Endpoints

**GET** `/config/categories`
- Function: get_bill_categories

**GET** `/config/split-methods`
- Function: get_split_methods

#### Detailed communications Endpoints

**GET** `/config/categories`
- Function: get_announcement_categories

**GET** `/config/priorities`
- Function: get_priority_levels

#### Detailed dashboard Endpoints

**GET** `/config/widgets`
- Function: get_available_widgets

**GET** `/config/layouts`
- Function: get_dashboard_layouts

#### Detailed event Endpoints

**GET** `/events`
- Function: get_events

**GET** `/events/pending-approval`
- Function: get_pending_events

**PUT** `/events/{event_id}/approve`
- Function: approve_event

**PUT** `/events/{event_id}/deny`
- Function: deny_event

**PUT** `/events/{event_id}/cancel`
- Function: cancel_event

**POST** `/events/{event_id}/rsvp`
- Function: create_rsvp

**GET** `/events/{event_id}/rsvps`
- Function: get_event_rsvps

**GET** `/my-events`
- Function: get_my_upcoming_events

**POST** `/check-conflicts`
- Function: check_scheduling_conflicts

**POST** `/suggest-times`
- Function: suggest_alternative_times

**GET** `/schedule-overview`
- Function: get_schedule_overview

**GET** `/statistics`
- Function: get_event_statistics

#### Detailed expenses Endpoints

**GET** `/config/categories`
- Function: get_expense_categories

**GET** `/config/split-methods`
- Function: get_split_methods

#### Detailed guests Endpoints

**GET** `/config/relationship-types`
- Function: get_relationship_types

#### Detailed households Endpoints

**GET** `/config/roles`
- Function: get_household_roles

#### Detailed notifications Endpoints

**GET** `/system/scheduler-status`
- Function: get_scheduler_status

**GET** `/config/types`
- Function: get_notification_types

**GET** `/config/priorities`
- Function: get_priority_levels

#### Detailed shopping Endpoints

**GET** `/config/categories`
- Function: get_shopping_categories

#### Detailed tasks Endpoints

**GET** `/config/priorities`
- Function: get_task_priorities

**GET** `/config/statuses`
- Function: get_task_statuses


## Project Structure

```
FastAPI Router Files Found:
./auth.py
./bills.py
./communications.py
./dashboard.py
./event.py
./expenses.py
./guests.py
./households.py
./notifications.py
./shopping.py
./tasks.py
```

## Route Patterns Analysis

### Routes by Router:

**auth** (7 endpoints)
- GET `/me`
- GET `/profile`
- POST `/change-password`
- POST `/login`
- POST `/logout`
- POST `/refresh-token`
- POST `/register`

**bills** (12 endpoints)
- DELETE `/{bill_id}`
- GET `/`
- GET `/config/categories`
- GET `/config/split-methods`
- GET `/overdue`
- GET `/summary`
- GET `/upcoming`
- GET `/{bill_id}`
- GET `/{bill_id}/payment-history`
- POST `/`
- POST `/{bill_id}/payments`
- PUT `/{bill_id}`

**communications** (18 endpoints)
- DELETE `/announcements/{announcement_id}`
- DELETE `/polls/{poll_id}`
- GET `/announcements`
- GET `/announcements/{announcement_id}`
- GET `/config/categories`
- GET `/config/priorities`
- GET `/house-rules`
- GET `/polls`
- GET `/polls/{poll_id}`
- GET `/summary`
- POST `/announcements`
- POST `/polls`
- POST `/polls/{poll_id}/vote`
- PUT `/announcements/{announcement_id}`
- PUT `/announcements/{announcement_id}/pin`
- PUT `/house-rules`
- PUT `/polls/{poll_id}`
- PUT `/polls/{poll_id}/close`

**dashboard** (15 endpoints)
- GET `/`
- GET `/config/layouts`
- GET `/config/widgets`
- GET `/financial-snapshot`
- GET `/health-check`
- GET `/household-pulse`
- GET `/mobile`
- GET `/notifications-summary`
- GET `/quick-actions`
- GET `/quick-stats`
- GET `/recent-activity`
- GET `/task-progress`
- GET `/upcoming-events`
- GET `/urgent-items`
- POST `/refresh`

**event** (13 endpoints)
- GET `/events`
- GET `/events/pending-approval`
- GET `/events/{event_id}/rsvps`
- GET `/my-events`
- GET `/schedule-overview`
- GET `/statistics`
- POST `/`
- POST `/check-conflicts`
- POST `/events/{event_id}/rsvp`
- POST `/suggest-times`
- PUT `/events/{event_id}/approve`
- PUT `/events/{event_id}/cancel`
- PUT `/events/{event_id}/deny`

**expenses** (13 endpoints)
- DELETE `/{expense_id}`
- GET `/`
- GET `/config/categories`
- GET `/config/split-methods`
- GET `/me/payment-history`
- GET `/me/summary`
- GET `/statistics/household`
- GET `/{expense_id}`
- POST `/`
- POST `/preview-split`
- POST `/{expense_id}/payments`
- PUT `/{expense_id}`
- PUT `/{expense_id}/split/{user_id}/mark-paid`

**guests** (12 endpoints)
- DELETE `/{guest_id}`
- GET `/`
- GET `/calendar`
- GET `/config/relationship-types`
- GET `/pending`
- GET `/policies`
- GET `/statistics`
- GET `/{guest_id}`
- POST `/`
- PUT `/policies`
- PUT `/{guest_id}/approve`
- PUT `/{guest_id}/deny`

**households** (16 endpoints)
- DELETE `/me/members/{user_id}`
- GET `/config/roles`
- GET `/me`
- GET `/me/health-score`
- GET `/me/members`
- GET `/me/statistics`
- GET `/me/summary`
- GET `/{household_id}`
- POST `/`
- POST `/join`
- POST `/me/invite`
- POST `/me/leave`
- POST `/me/members`
- POST `/me/transfer-ownership`
- PUT `/me`
- PUT `/me/members/{user_id}/role`

**notifications** (16 endpoints)
- DELETE `/{notification_id}`
- GET `/`
- GET `/config/priorities`
- GET `/config/types`
- GET `/preferences`
- GET `/summary`
- GET `/system/scheduler-status`
- GET `/unread-count`
- GET `/{notification_id}`
- POST `/system/trigger/all-reminders`
- POST `/system/trigger/bill-reminders`
- POST `/system/trigger/event-reminders`
- POST `/system/trigger/task-reminders`
- PUT `/mark-all-read`
- PUT `/preferences`
- PUT `/{notification_id}/read`

**shopping** (16 endpoints)
- DELETE `/lists/{list_id}`
- DELETE `/lists/{list_id}/items/{item_id}`
- GET `/config/categories`
- GET `/lists`
- GET `/lists/{list_id}`
- GET `/lists/{list_id}/items`
- GET `/me/assignments`
- GET `/statistics`
- GET `/templates`
- POST `/lists`
- POST `/lists/{list_id}/items`
- PUT `/lists/{list_id}`
- PUT `/lists/{list_id}/complete`
- PUT `/lists/{list_id}/items/{item_id}`
- PUT `/lists/{list_id}/items/{item_id}/purchased`
- PUT `/lists/{list_id}/reassign`

**tasks** (17 endpoints)
- DELETE `/{task_id}`
- GET `/`
- GET `/config/priorities`
- GET `/config/statuses`
- GET `/leaderboard/current`
- GET `/me`
- GET `/me/score`
- GET `/overdue`
- GET `/rotation/schedule`
- GET `/statistics/household`
- GET `/{task_id}`
- POST `/`
- POST `/bulk/reassign`
- PUT `/{task_id}`
- PUT `/{task_id}/complete`
- PUT `/{task_id}/reassign`
- PUT `/{task_id}/status`

### Common Route Patterns:

**`/`** - POST (bills), GET (bills), GET (dashboard), POST (event), POST (expenses), GET (expenses), POST (guests), GET (guests), POST (households), GET (notifications), POST (tasks), GET (tasks)
**`/announcements`** - POST (communications), GET (communications)
**`/announcements/{id}`** - GET (communications), PUT (communications), DELETE (communications)
**`/config/categories`** - GET (bills), GET (communications), GET (expenses), GET (shopping)
**`/config/priorities`** - GET (communications), GET (notifications), GET (tasks)
**`/config/split-methods`** - GET (bills), GET (expenses)
**`/house-rules`** - GET (communications), PUT (communications)
**`/lists`** - POST (shopping), GET (shopping)
**`/lists/{id}`** - GET (shopping), PUT (shopping), DELETE (shopping)
**`/lists/{id}/items`** - POST (shopping), GET (shopping)
**`/lists/{id}/items/{id}`** - PUT (shopping), DELETE (shopping)
**`/me`** - GET (auth), GET (households), PUT (households), GET (tasks)
**`/me/members`** - GET (households), POST (households)
**`/me/summary`** - GET (expenses), GET (households)
**`/overdue`** - GET (bills), GET (tasks)
**`/policies`** - GET (guests), PUT (guests)
**`/polls`** - POST (communications), GET (communications)
**`/polls/{id}`** - GET (communications), PUT (communications), DELETE (communications)
**`/preferences`** - GET (notifications), PUT (notifications)
**`/statistics`** - GET (event), GET (guests), GET (shopping)
**`/statistics/household`** - GET (expenses), GET (tasks)
**`/summary`** - GET (bills), GET (communications), GET (notifications)
**`/{id}`** - GET (bills), PUT (bills), DELETE (bills), GET (expenses), PUT (expenses), DELETE (expenses), GET (guests), DELETE (guests), GET (households), GET (notifications), DELETE (notifications), GET (tasks), PUT (tasks), DELETE (tasks)
**`/{id}/payments`** - POST (bills), POST (expenses)

**Total Endpoints:** 155
**Total Routers:** 11
