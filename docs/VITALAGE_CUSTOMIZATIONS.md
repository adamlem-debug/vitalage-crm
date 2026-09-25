# VitalAge CRM Customizations

> Canonical technical inventory for the VitalAge fork of Frappe CRM.
>
> **Repository:** `adamlem-debug/vitalage-crm`  
> **Stable branch:** `vitalage-main`  
> **Current reconciliation branch:** `chore/upstream-fixes-2026-09-24`  
> **Document baseline:** 2026-09-25  
> **Upstream lineage:** forked from Frappe CRM `main` around 2026-07-07 (merge base `ead04d4b95455f1673b477cfb4b4ac017ce3d4e9`).

## 1. Why this document exists

VitalAge is not a stock Frappe CRM deployment. It has two customization layers:

1. **Repository-level customizations** — Python, Vue/JavaScript, DocType definitions, hooks, patches, permissions, tests, and CI. These are version-controlled in this repository.
2. **Site-level Frappe customizations** — Custom Fields, Server Scripts, roles, field layouts, view settings, Google Calendar records, and other Frappe Desk configuration stored in the site database. These are **not necessarily present in Git**.

Both layers are production-critical. A future upstream merge must preserve both.

---

# 2. Functional customization map

## 2.1 CRM terminology and operating model

VitalAge uses Frappe CRM as a clinic/client-management system rather than a conventional sales CRM.

Key business concepts:

- **CRM Lead** — prospective client.
- **CRM Deal** — presented to users as **Client case**.
- **CRM Contact** — person/contact record.
- **CRM Task** — operational/clinical task and calendar source.
- **FCRM Note** — clinical note/dekurz.
- **Care Plan** — site-level child-table workflow for supplements, medication, and checkups.
- **Event / Google Calendar** — calendar projection of eligible CRM Tasks.

The fork should therefore not be evaluated solely against upstream sales CRM behavior.

---

# 3. Lead customizations

## 3.1 Lead conversion

VitalAge has a custom **Convert to Customer** flow.

Expected behavior:

- Creates or links a Contact.
- Marks the Lead as **Converted**.
- VitalAge historically hides/replaces the stock **Convert to Deal** workflow in the production UI.
- Lead-to-contact relationships remain visible from the Contact context.

Site-specific Lead fields include billing/customer information such as:

- Address
- IČO
- DIČ
- Country

These fields are site configuration and may be implemented as Frappe Custom Fields rather than schema committed in this repository.

## 3.2 Lead views

Operational default:

- **CRM Lead:** Group by **Status**.

Default-view behavior depends on the CRM View Settings/router customizations described later.

## 3.3 Lead task types

VitalAge Lead tasks are restricted to Lead-specific operational values, including:

- Domluvit vstupní konzultaci
- Domluvit odběr
- Kontaktovat později
- Discovery call

Task Type is site-configured through the custom `custom_task_type` field and form logic.

---

# 4. Client case / CRM Deal customizations

## 4.1 Deal renamed to Client case

The user-facing concept of CRM Deal is **Client case**.

Do not assume upstream labels, actions, product-centric UI, or sales-stage behavior are appropriate for this deployment.

## 4.2 VitalAge Client case statuses

The production status model includes:

- Bez členství
- Monitoring
- Management
- Párový
- Neaktivní
- Ztracen

These statuses are site data/configuration, not necessarily hard-coded in the repository.

## 4.3 Membership fields

Known production fields include:

- `custom_membership_start_date`
- `custom_membership_end_date`

Membership dates define when service allocations are active.

If today is outside the inclusive membership range, automatic Included allocations are zero.

## 4.4 General consultation allocation

Known fields:

- `custom_consultations_included`
- General Used
- General Remaining
- General Extra Paid

Business rules:

- Monitoring: **1.0 General Included**
- Management: **6.0 General Included**
- Other/inactive membership: **0**

Task consumption:

- Consultation = 1.0 General
- Other consultation = 1.0 General
- Nutritional consultation = 0.5 General
- Other task types = 0 General

Only tasks with status **Done** count toward Used.

Task due date must fall inside the active membership period to count.

Extra Paid can offset over-consumption; Remaining may go negative before Extra Paid is applied.

## 4.5 Concierge allocation

Known fields:

- `custom_concierge` — enables Concierge service.
- `custom_concierge_included`
- Concierge Used
- Concierge Remaining
- Concierge Extra Paid

Current intended rule (changed 2026-09-25):

| Status | Concierge enabled | Included |
| --- | --- | ---: |
| Monitoring | No | 0 |
| Monitoring | Yes | 2 |
| Management | No | 0 |
| Management | Yes | 6 |
| Other/inactive membership | Either | 0 |

Concierge tasks consume 1.0 Concierge unit and require `custom_concierge` to be enabled.

## 4.6 Nutrition

Known field:

- `custom_nutrition`

Nutrition does **not** have its own Included/Used/Remaining bucket.

Instead:

- enabling Nutrition permits Nutritional consultation tasks;
- Nutritional consultation consumes **0.5 General**.

A Nutrition specialist link to User is also used operationally on Client cases.

## 4.7 Other site-level Client case fields

The production site additionally uses fields for operational/billing state, including:

- Payment Signal
- Services
- Invoice Issued
- Invoice Paid
- client email used for Task notifications
- Nutrition specialist

These should be treated as production-critical Custom Fields even when their definitions are not present in Git.

---

# 5. Care Plan

Care Plan is a VitalAge-specific site workflow attached to Client cases.

Known row fields:

- Type
- Start Date
- End Date
- Note
- Owner

Known types:

- Supplements
- Medication
- Checkups

Expected access model:

- visible to relevant users;
- editing restricted according to VitalAge role/permission setup;
- historically intended to be editable only by privileged/admin users where permlevel configuration applies.

## 5.1 Care Plan reminders

Care Plan reminder logic is site-level and implemented with a Frappe **Scheduler Event Server Script**, not repository Python.

Server Script:

- **Care Plan End Date Reminders**

Reminder offsets:

- Supplements: **17 days before End Date**
- Medication: **10 days before End Date**
- Checkups: **28 days before End Date**

Recipient:

- Owner/responsible User on the Care Plan row.

The deployment also uses Email Queue/background mail delivery after the reminder script queues the email.

Because this script is stored in the Frappe site database, its source should be exported/backed up separately if disaster recovery or site recreation is required.

---

# 6. CRM Task customizations

## 6.1 Custom Task Type

Production uses a mandatory custom field:

- `custom_task_type`

Known Client-case Task Types include:

- Consultation
- Nutritional consultation
- Sample collection
- Therapy
- External Partner Coordination
- Other consultation
- Administration
- Concierge
- Poslat suplementy
- Poslat probiotika
- Nasadit CGM

Lead and Client-case contexts expose different allowed Task Types.

The Task Type field/filter behavior is implemented partly through site-level configuration/form scripts, so a fresh site cannot be reconstructed from Git alone without the corresponding Custom Fields/scripts.

## 6.2 Duration

Production calendar-eligible tasks use:

- `custom_duration`

Supported operational values:

- 30
- 60
- 90
- 120 minutes

## 6.3 Task status

The fork includes the technical status:

- **Removed from Calendar**

This is used when an externally deleted Google Calendar Event is reconciled back into CRM.

It is intentionally filtered from normal user-selectable status options in the Task activity UI.

## 6.4 Task Participants — multi-user assignment

Introduced during the 2026-09 upstream reconciliation.

Files:

- `crm/fcrm/doctype/crm_task_participant/crm_task_participant.json`
- `crm/fcrm/doctype/crm_task_participant/crm_task_participant.py`
- `crm/fcrm/doctype/crm_task/crm_task.json`
- `crm/fcrm/doctype/crm_task/crm_task.py`
- `crm/patches/v1_0/add_task_participants_to_quick_entry.py`
- `crm/patches.txt`
- `crm/install.py`
- `crm/fcrm/doctype/crm_task/test_crm_task.py`

Data model:

- CRM Task now has `participants` as **Table MultiSelect**.
- Child DocType: **CRM Task Participant**.
- Each row links to **User**.

Behavior:

- `assigned_to` remains the **primary assignee**.
- Participants are real additional Frappe Task assignees via ToDo assignments.
- Desired assignment set = primary assignee + Participants.
- Removing a participant removes that user's Task assignment.
- Frappe assignment helpers mutate the physical `assigned_to` field, so `CRMTask.sync_assignments()` explicitly restores the primary assignee after syncing ToDos.

Critical invariant:

> Adding/removing Participants must never silently change the primary `assigned_to`.

## 6.5 Task activity-row metadata

Files:

- `frontend/src/components/Activities/TaskArea.vue`
- `crm/api/activities.py`

VitalAge activity rows show:

**Assigned To · Due Date · Task Type · Status**

Priority was deliberately removed from this compact activity-row metadata.

## 6.6 Task deletion

Files:

- `frontend/src/components/Activities/AllModals.vue`
- `crm/hooks.py`
- `crm/fcrm/task_calendar_sync.py`

Deletion behavior is customized because CRM Task can be linked to generated Event records.

Before Frappe performs linked-document validation:

- CRM Notifications referencing the Task are removed.
- linked/historical calendar Events are removed.

After deletion:

- a final asynchronous calendar-history cleanup is queued.

The cleanup is defensive on fresh sites where the custom Event field `custom_crm_task_name` may not yet exist.

---

# 7. CRM Task quota / consultation accounting

This logic is primarily implemented as **site-level Server Scripts**.

Known active scripts from the production site:

- **CRM Deal - Consultation allocation**
- **CRM Deal - Consultation recalculation**
- **CRM Task - Consultation validation and recalculation**
- **CRM Task - Consultation recalculation after delete**
- **Refresh membership allocations**

Important business behavior:

- Only Done Tasks count as Used.
- Task date must be within membership dates.
- Consultation / Nutrition / Concierge require valid membership dates.
- Nutrition requires `custom_nutrition`.
- Concierge requires `custom_concierge`.
- General and Concierge Remaining may become negative to indicate extra billable use.
- Extra Paid offsets the negative balance.

## 7.1 CRM Deal - Consultation allocation

This Server Script is the source of automatic Included values.

As of 2026-09-25 the intended rule is:

- inactive membership: General 0 / Concierge 0
- Monitoring: General 1; Concierge 2 only when `custom_concierge` is enabled
- Management: General 6; Concierge 6 only when `custom_concierge` is enabled

## 7.2 Refresh membership allocations

Scheduler Event Server Script.

It finds:

- memberships starting today;
- memberships that ended yesterday;

and saves those CRM Deals so the allocation/recalculation scripts run.

This is intentionally a trigger/orchestrator and does not duplicate the allocation table.

---

# 8. Task → Event → Google Calendar integration

This is one of the most production-critical VitalAge customizations.

Primary implementation:

- `crm/fcrm/task_calendar_sync.py`
- `crm/hooks.py`

Related schema/site fields:

- CRM Task `custom_duration`
- CRM Task `custom_calendar_event`
- CRM Task `custom_task_type`
- Event `custom_crm_task_name`
- Google Calendar records belonging to Frappe Users
- calendar eligibility/cancellation configuration on the site

## 8.1 Lifecycle

CRM Task update:

`CRM Task on_update -> queue_task_calendar_sync -> sync_task_calendar_event`

CRM Task delete:

`on_trash -> notification/Event cleanup -> delete -> after_delete history cleanup`

The sync job is queued only after the Task transaction commits.

## 8.2 Event creation

An Event is created when all required conditions are true:

- Task Type is calendar-enabled.
- Task is not in a cancellation/external-removal status.
- primary `assigned_to` exists.
- `due_date` exists.
- `custom_duration` exists.
- primary user has an enabled, push-enabled Google Calendar.

Generated Event:

- Public
- starts at Task `due_date`
- ends at due date + duration
- syncs with Google Calendar
- stores `custom_crm_task_name`
- Task stores the current Event in `custom_calendar_event`

## 8.3 Participants → Event attendees

Additional Task Participants become Frappe Event Participants.

Important implementation detail:

- User document name is **not assumed to be an email address**.
- The code resolves the actual User `email` field before sending Google attendee data.
- This is required for special users such as `Administrator`.

Primary `assigned_to` remains the calendar owner/organizer and is not duplicated in Event Participants.

## 8.4 Update/reassignment

Task changes update the current Event:

- title/subject
- description
- starts_on
- ends_on
- Google Calendar
- Event participants

If the primary assignee changes to a user with a different Google Calendar:

- the old active Event is removed;
- a new Event is created in the new primary user's calendar.

## 8.5 Cancellation/reactivation

Configured cancellation statuses retain a terminal Event as history.

If the Task is later reactivated:

- the old terminal Event remains historical;
- a new active Event is created.

## 8.6 External Google deletion reconciliation

Scheduler hook in `crm/hooks.py`:

- runs every 15 minutes;
- calls `crm.fcrm.task_calendar_sync.reconcile_external_calendar_removals`.

Frappe's Google pull sync marks deleted/cancelled Google Events as Closed.

VitalAge then:

- verifies that the Closed Event is still the Task's current Event;
- ignores intentionally cancelled Tasks;
- moves the Task to the configured external-removal status (normally **Removed from Calendar**);
- deliberately uses direct DB update so Task `on_update` does not immediately recreate the Event.

### Upstream-merge warning

**Do not accept upstream changes that remove or materially replace CRM Task Calendar behavior without explicitly re-porting this integration.**

---

# 9. Quick Entry / form-controller behavior

Files:

- `frontend/src/components/Modals/DoctypeModal.vue`
- `frontend/src/data/document.js`

VitalAge relies heavily on CRM Form Scripts and runtime field-property changes.

A race/stale-state fix was introduced in September 2026:

- form-controller initialization is awaitable;
- concurrent callers wait for the same setup promise;
- new Quick Entry documents reset document and field-property state before scripts execute.

This specifically prevents intermittent cases where Task Type options were blank until an unrelated Client case save/reload occurred.

This code is upstream-sensitive because changes to Frappe CRM form-controller lifecycle can easily reintroduce stale Quick Entry behavior.

---

# 10. Notifications and email

## 10.1 Task notifications

Production behavior includes Task notifications to the Client case email for selected Task Types, including operational appointment/service types such as:

- Consultation
- Nutritional consultation
- Sample collection
- Therapy

Canceled/Done tasks are excluded according to the site script logic.

Known site Server Script:

- **Daily notifications at 06:00**

Known Client-case email synchronization script:

- **CRM Deal - Sync Task Client Email**

These are site-level and must be backed up outside Git.

## 10.2 Care Plan notifications

See Care Plan section.

## 10.3 Email Queue

Frappe Server Scripts queue mail; delivery is handled by Frappe's normal background email queue processing.

Operational troubleshooting order:

1. confirm the scheduler script ran;
2. inspect Email Queue;
3. inspect error/retry state;
4. confirm recipient User/email;
5. inspect mail account/background jobs.

---

# 11. FCRM Note

Production FCRM Notes use a mandatory clinical **Type** field.

Known values:

- Lékařský dekurz
- Nutriční dekurz
- Sesterský dekurz

Activity API reads `custom_type` when returning linked notes.

This field is site-level Custom Field configuration and is not defined in the stock `fcrm_note.json` currently in the repository.

---

# 12. Roles and permissions

Known VitalAge roles include:

- VitalAge Master Admin
- Admin pobočky
- Lékař
- Nutriční
- Sestra
- Health Coordinator
- VitalAge Physician

These roles and their DocPerm/User Permission setup are site-level data unless explicitly exported.

## 12.1 Repository-level hierarchy permissions

Files:

- `crm/permissions/org_hierarchy.py`
- `crm/hooks.py`
- `crm/fcrm/doctype/fcrm_settings/fcrm_settings.json`

FCRM Settings includes:

- `enable_sales_hierarchy`

When enabled:

- Lead and Deal read visibility is restricted by CRM Sales Hierarchy.
- Managers in the hierarchy can see records owned by/assigned to users in their subtree.
- Sales Users see own/assigned records.
- Administrator/System Manager bypass hierarchy restrictions.

Hooks:

- `permission_query_conditions` for CRM Lead and CRM Deal
- `has_permission` for CRM Lead and CRM Deal

---

# 13. CRM View / routing customizations

Files:

- `crm/fcrm/doctype/crm_view_settings/crm_view_settings.py`
- `frontend/src/router.js`
- view-store/frontend files touched by reconciliation

Operational defaults:

- Leads -> Group by Status
- Client cases/Deals -> Group by Owner

Important custom behavior:

- standard view state is preserved during routine filter/column saves;
- router resolves saved/default views per DocType;
- invalid legacy view routes are normalized;
- last active Lead/Deal tab is remembered.

Upstream changes to view routing/default resolution need regression testing against these defaults.

---

# 14. ERPNext integration

VitalAge currently does not actively use CRM Products operationally; product UI is hidden/not part of normal workflow.

The repository nevertheless retains ERPNext compatibility code because the app supports ERPNext integration.

Relevant areas include:

- customer creation/synchronization
- Sales Order customer behavior
- Item/product synchronization
- product rate lookup
- ERPNext v15 Item Price compatibility

Do not remove these files casually: they are covered by automated tests and may become operationally relevant later, but they are lower priority for manual VitalAge regression testing today.

---

# 15. FCRM Settings / repository settings

Primary files:

- `crm/fcrm/doctype/fcrm_settings/fcrm_settings.json`
- `crm/fcrm/doctype/fcrm_settings/fcrm_settings.py`

Notable settings include:

- Enable Forecasting
- Enable Sales Hierarchy Permissions
- Auto update Expected Deal Value
- Timeline timestamp format
- Timeline sort order
- Currency
- Exchange rate provider
- Branding
- Standard dropdown items
- persona/onboarding completion state

Forecasting can dynamically modify Deal Quick Entry/Side Panel layouts and Property Setters.

---

# 16. Installation and migration

Files:

- `crm/install.py`
- `crm/patches.txt`
- `crm/patches/v1_0/add_task_participants_to_quick_entry.py`

Important VitalAge migration behavior:

- Task Participants are inserted into existing CRM Task Quick Entry layouts via patch.
- Fresh installs include Participants in the default Task Quick Entry.
- Existing sites are expected to migrate without manually rebuilding that layout.

Any schema or Quick Entry customization introduced later should have both:

1. fresh-install behavior;
2. upgrade patch behavior.

---

# 17. CI / upgrade safety

Relevant workflows:

- `.github/workflows/linters.yml`
- `.github/workflows/migration-test.yml`
- Server workflow
- Frontend workflow

VitalAge CI currently validates:

- semantic commits
- pre-commit formatting/lint
- Semgrep
- frontend lint/build/unit tests
- Frappe server tests against version-15
- Frappe server tests against version-16
- migration from `vitalage-main` to PR code

Migration mapping:

- `vitalage-main` -> Frappe `version-15`

Commit lint intentionally uses full git history because the reconciliation branch has deep ancestry and shallow checkout could not resolve the merge base.

---

# 18. September 2026 upstream reconciliation

The fork originally diverged from upstream Frappe CRM `main` around 2026-07-07.

At reconciliation time, the stable branch was approximately:

- 68 commits ahead of upstream main
- 657 commits behind upstream main

A wholesale upstream merge was deliberately avoided because it would have included broad architecture/UI changes and changes conflicting with VitalAge behavior.

Selected upstream work was backported/reconciled instead.

Examples include:

- CRM Forms/public forms
- auth/session routing fixes
- mobile quick filters
- email reply sender behavior
- attachment upload fixes
- details-panel persistence
- primary Deal contact handling
- employee-count propagation
- Role Profile safety
- assignment permission hardening
- call recording handling
- onboarding validation
- side-panel fixes
- pagination/filter hardening
- ERPNext pricing fixes
- org hierarchy SQL fixes
- notification session scoping
- email-template `doc` context
- saved-view dirty/default preservation
- system date formatting improvements

Explicitly deferred:

- Workflow Automations requiring `frappe.automation_engine`
- upstream changes that remove Calendar behavior needed by VitalAge
- Domain Enrichment redesign
- broad Vite/frappe-ui modernization
- Desk v2 migration
- nonessential Exotel/LDAP-only work
- large UI migrations immediately before production deployment

---

# 19. Site-level Server Script inventory

As observed on the VitalAge site on 2026-09-25:

| Server Script | Type | Reference | Purpose |
| --- | --- | --- | --- |
| Populate custom_client_full_name | DocType Event | CRM Deal | Populate client full name |
| Admin role assignment restriction | DocType Event | User | Restrict admin-role assignment; currently disabled |
| Care Plan End Date Reminders | Scheduler Event | — | Care Plan reminder emails |
| CRM Deal - Sync Task Client Email | DocType Event | CRM Deal | Keep Task notification/client email data synchronized |
| Refresh membership allocations | Scheduler Event | — | Re-save memberships at start/end boundaries |
| CRM Deal - Consultation allocation | DocType Event | CRM Deal | Set Included General/Concierge allocations |
| CRM Deal - Consultation recalculation | DocType Event | CRM Deal | Recalculate quota counters |
| CRM Task - Consultation recalculation after delete | DocType Event | CRM Task | Recalculate counters after Task deletion |
| CRM Task - Consultation validation and recalculation | DocType Event | CRM Task | Validate service/membership and recalculate quota use |
| Daily notifications at 06:00 | Scheduler Event | — | Daily operational Task notifications |
| Convert Lead to Customer | API | — | Legacy/custom conversion API; currently disabled |

**Important:** Server Script bodies are site data. Git deployment does not recreate them.

---

# 20. Site configuration that must be backed up separately

A repository clone alone is insufficient to recreate VitalAge production.

At minimum, preserve/export:

- Server Scripts listed above
- Custom Fields on CRM Lead
- Custom Fields on CRM Deal
- Custom Fields on CRM Task
- Custom Fields on FCRM Note
- Custom Field(s) on Event
- Care Plan child DocType/custom fields and permissions
- VitalAge roles and Role Profiles
- DocPerm / Custom DocPerm / permission-level configuration
- CRM Fields Layout records
- CRM View Settings / default views as appropriate
- VitalAge-specific Deal statuses
- Task Type field options and form filtering scripts
- Google Calendar records and user mapping
- Email Accounts and outbound mail configuration
- scheduled Server Script cron expressions
- any Property Setters
- any Client Scripts/CRM Form Scripts added directly on the site

Recommended long-term improvement:

> Export these site-level objects into fixtures or a dedicated VitalAge app/migration layer so that production can be recreated from source control rather than relying on database-only configuration.

---

# 21. High-risk files during future upstream merges

Treat changes to these files as requiring explicit VitalAge review:

### Calendar / Task

- `crm/fcrm/task_calendar_sync.py`
- `crm/hooks.py`
- `crm/fcrm/doctype/crm_task/crm_task.py`
- `crm/fcrm/doctype/crm_task/crm_task.json`
- `crm/fcrm/doctype/crm_task_participant/*`
- `crm/patches/v1_0/add_task_participants_to_quick_entry.py`

### Task/Activity UI

- `frontend/src/components/Activities/TaskArea.vue`
- `frontend/src/components/Activities/AllModals.vue`
- `crm/api/activities.py`

### Form-script lifecycle

- `frontend/src/components/Modals/DoctypeModal.vue`
- `frontend/src/data/document.js`
- `frontend/src/data/script.js`

### Views/routing

- `frontend/src/router.js`
- `crm/fcrm/doctype/crm_view_settings/crm_view_settings.py`

### Permissions

- `crm/permissions/org_hierarchy.py`
- related hooks in `crm/hooks.py`

### Install/migration

- `crm/install.py`
- `crm/patches.txt`

If upstream changes one of these areas, compare behavior rather than just resolving textual conflicts.

---

# 22. Required regression areas after upstream work

Minimum regression suite before production:

1. Lead create/edit/conversion.
2. Client case create/edit/status and existing-record load.
3. Membership dates and automatic allocation.
4. General/Nutrition/Concierge quota accounting.
5. Task create/edit/status/delete.
6. Task Type options on first open.
7. Participants assignment lifecycle.
8. Task -> Event -> Google Calendar lifecycle.
9. Google external deletion reconciliation.
10. Care Plan reminders.
11. Task/client email notifications.
12. FCRM Note types.
13. permissions/role visibility.
14. default Lead/Deal views.
15. migration from current production/stable branch.

---

# 23. Current Participants/calendar acceptance contract

A valid implementation must satisfy all of the following:

1. Primary-only Task works exactly as before.
2. Participants can contain multiple Users.
3. primary + Participants all receive Task assignments.
4. adding Participants never changes primary `assigned_to`.
5. removing a Participant removes only that user's assignment.
6. calendar-eligible Task creates one current Frappe Event.
7. Event belongs to primary assignee's Google Calendar.
8. additional Participants become Event/Google attendees.
9. attendee email is resolved from the User record.
10. changing Participants updates attendees.
11. changing Task date/time/duration updates Event.
12. changing primary assignee moves/recreates Event as needed.
13. cancellation produces terminal calendar state.
14. reactivation creates a new active Event.
15. Task deletion removes linked Event(s) and does not fail link validation.
16. external Google deletion eventually moves Task to Removed from Calendar and does not recreate it immediately.

---

# 24. Source-of-truth policy

When behavior differs between this document, repository code, and Frappe site configuration:

1. **Repository code** is source of truth for version-controlled behavior.
2. **Current production/dev site records** are source of truth for database-only customizations.
3. Business-rule changes should be documented here at the same time they are introduced.
4. Site-only changes should ideally be exported into source control to reduce configuration drift.

