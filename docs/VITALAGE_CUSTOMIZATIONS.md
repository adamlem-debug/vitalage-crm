# VitalAge CRM Customizations

> Canonical technical inventory for the VitalAge fork of Frappe CRM.
>
> **Repository:** `adamlem-debug/vitalage-crm`  
> **Stable branch:** `vitalage-main`  
> **Development branch:** `vitalage-dev`  
> **Configuration-as-code baseline:** established 2026-09-29 and maintained continuously  
> **Document baseline:** 2026-09-29  
> **Upstream lineage:** forked from Frappe CRM `main` around 2026-07-07 (merge base `ead04d4b95455f1673b477cfb4b4ac017ce3d4e9`).

## 1. Why this document exists

VitalAge is not a stock Frappe CRM deployment. It has two customization layers:

1. **Repository-level customizations** — Python, Vue/JavaScript, DocType definitions, hooks, patches, permissions, tests, and CI. These are version-controlled in this repository.
2. **Site-level Frappe customizations** — Custom Fields, Server Scripts, roles, field layouts, view settings, Google Calendar records, and other Frappe Desk configuration stored in the site database. These are **not necessarily present in Git**.

Both layers are production-critical. A future upstream merge must preserve both.

## 1.1 Standing rule for every future customization

Every future CRM change must include an explicit **configuration-as-code decision** before it is promoted from DEV to PROD.

Use this rule:

- If the change is already represented by normal source-controlled app code (Python, Vue/JavaScript, hooks, DocType JSON, patches, tests, etc.), normal Git deployment is sufficient.
- If the change is created or changed in Desk and is stored in the site database, decide whether PROD must be able to reproduce it on a fresh site.
- If the answer is yes, capture it in Git using the appropriate mechanism before promotion to PROD:
  - fixture,
  - `vitalage_config_payload.json`,
  - `apply_vitalage_site_config()` / after-migrate bootstrap logic,
  - patch, or
  - another explicit source-controlled migration mechanism.
- If the setting contains credentials, tokens, passwords, OAuth state, mailbox secrets, API secrets, or other environment-specific values, **do not** commit those values. Document the manual/environment-specific setup instead.
- Business/client data is never part of this configuration migration.

Examples of site-level changes that require this decision include:

- Custom Fields
- Property Setters
- Server Scripts
- CRM Form Scripts
- custom DocTypes created in Desk
- Roles, Role Profiles and Custom DocPerm changes
- CRM Fields Layouts
- statuses and Lead Sources
- Notifications
- default CRM views
- settings stored in Single DocTypes
- other configuration records required for VitalAge behavior

### Promotion gate

Before every future `vitalage-dev -> vitalage-main` promotion, ask:

> **Does this change rely on any DEV database configuration that a fresh PROD deployment would not recreate from Git?**

If yes, the migration/config-as-code setup must be extended as part of the same change before PROD deployment.

This decision is now part of the standard VitalAge development workflow, not an optional cleanup step.

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


## 3.4 External Lead creation REST API

VitalAge accepts externally created Leads through Frappe's **standard REST resource API** for the `CRM Lead` DocType.

This is **not** a custom VitalAge Server Script or a dedicated Python endpoint, so there is no separate endpoint definition to find in the Server Script list.

### Endpoint

Current DEV endpoint:

```text
POST https://vitalageclinic.frappe.cloud/api/resource/CRM%20Lead
```

Equivalent Frappe resource path:

```text
POST /api/resource/CRM%20Lead
```

### Authentication

Use Frappe token authentication:

```http
Authorization: token <API_KEY>:<API_SECRET>
Content-Type: application/json
```

Current DEV integration credentials are configured on the Frappe User used by Adam for administration/testing.

**Do not commit the API key or API secret to Git.** The API secret is supplied out-of-band to the calling system and should be stored in its secret store.

Security note:

> The current DEV integration uses an administrative user. Before production cutover, prefer a dedicated integration User with only the roles/permissions required to create CRM Leads.

### Current DEV request contract

The web integration was instructed to send:

```json
{
  "lead_name": "Postman TEST3",
  "first_name": "Postman",
  "last_name": "TEST3",
  "email": "postman_test_v3@vitalage.cz",
  "mobile_no": "+420123456789",
  "source": "Website",
  "custom_source_detail": "contact_form",
  "custom_description": "Ahoj"
}
```

Field meaning:

- `first_name` — currently the only mandatory field in the DEV contract.
- `last_name` — optional surname.
- `lead_name` — optional explicit display/full-name value.
- `email` — optional client email.
- `mobile_no` — optional client mobile number.
- `source` — should currently be sent as **Website**.
- `custom_source_detail` — site-level single-line text field for the specific website source/form, e.g. `contact_form`.
- `custom_description` — site-level multi-line text field for the client's free-text message.

The required-field contract may change before/at production go-live and must be kept in sync with the website integration.

### Validation / creation behavior

Source files:

- `crm/fcrm/doctype/crm_lead/crm_lead.json`
- `crm/fcrm/doctype/crm_lead/crm_lead.py`

Important behavior:

- `first_name` is mandatory in the committed `CRM Lead` schema.
- if `status` is omitted on a new Lead, CRM Lead validation assigns **New** when that status exists; otherwise it uses the first open Lead status.
- `lead_name` is derived from the person's name when the document is validated.
- email format is validated when `email` is supplied.
- Lead Owner cannot be the same address as the Lead email.
- the Lead naming series is generated automatically.
- normal Frappe DocType permissions apply to the API User.

The standard Frappe resource API returns the created document in the normal REST response under `data`.

### Where to inspect this integration on the site

Because the endpoint is generated automatically by Frappe, its configuration is split between code and site data:

1. **REST route:** standard Frappe `/api/resource/<DocType>` behavior.
2. **Lead schema:** `crm/fcrm/doctype/crm_lead/crm_lead.json`.
3. **Lead validation/hooks:** `crm/fcrm/doctype/crm_lead/crm_lead.py`.
4. **Authentication:** Desk -> User -> integration/admin User -> Settings -> API Access.
5. **Permissions:** the integration User's Roles & Permissions plus CRM Lead DocType permissions.
6. **Site-specific fields:** Customize Form / Custom Field records for `custom_source_detail`, `custom_description`, and any other Lead custom fields.

If this integration is changed to a custom whitelisted method or Server Script API in the future, document the exact method name, authentication contract, payload, validation, and response here and add the implementation to source control where possible.


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
- 45
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

## 8.1 Calendar-enabled Task Types

Task -> Event -> Google Calendar sync is intentionally limited to selected Task Types.

Current production calendar-enabled Task Types (verified in **VitalAge CRM Settings** on 2026-09-25):

- Consultation
- Nutrition consultation
- Concierge
- Sample collection
- Therapy
- Other consultation
- Discovery call

Other Task Types do not create/sync Frappe Events or Google Calendar events.

The list is **configuration-driven**, not hardcoded in `task_calendar_sync.py`. It is read from the `calendar_task_types` child table in **VitalAge CRM Settings** by `get_calendar_settings()`.

Current related production settings:

- Calendar Cancellation Statuses: **Canceled**
- External Calendar Removal Status: **Removed from Calendar**

This means the enabled Task Type list and calendar status behavior can be changed administratively without changing Python code. If the site configuration is changed, this document should be updated at the same time.

## 8.2 Lifecycle

CRM Task update:

`CRM Task on_update -> queue_task_calendar_sync -> sync_task_calendar_event`

CRM Task delete:

`on_trash -> notification/Event cleanup -> delete -> after_delete history cleanup`

The sync job is queued only after the Task transaction commits.

## 8.3 Event creation

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

## 8.4 Participants → Event attendees

Additional Task Participants become Frappe Event Participants.

Important implementation detail:

- User document name is **not assumed to be an email address**.
- The code resolves the actual User `email` field before sending Google attendee data.
- This is required for special users such as `Administrator`.

Primary `assigned_to` remains the calendar owner/organizer and is not duplicated in Event Participants.

## 8.5 Update/reassignment

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

## 8.6 Cancellation/reactivation

Configured cancellation statuses retain a terminal Event as history.

If the Task is later reactivated:

- the old terminal Event remains historical;
- a new active Event is created.

## 8.7 External Google deletion reconciliation

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

Production behavior includes Task notifications to the Client case email for selected Task Types, including:

- Consultation
- Nutritional consultation
- Sample collection
- Therapy

Canceled/Done tasks are excluded according to the site script logic.

Known site Server Script:

- **Daily notifications at 06:00**

Known Client-case email synchronization script:

- **CRM Deal - Sync Task Client Email**

The 2026-09-29 broad DEV-vs-clean-PROD audit also identified two VitalAge-specific Notification records that were not included in the original migration export:

1. **Client notification**
   - Notification DocType: CRM Task
   - email recipient comes from custom_client_email
   - sender account: **Vital Age Clinic Admin**
   - subject: Vital Age Clinic Reminder: {{ doc.title }}
   - DEV contains a BCC address; BCC/sender credentials are environment-specific/private and are not committed

2. **Consultation Reminder - 7 Days**
   - Notification DocType: CRM Task
   - condition applies to Consultation / Nutrition consultation tasks
   - recipient is the assigned Task user
   - send_to_all_assignees = 1
   - sender account: **Vital Age Clinic Admin**
   - subject: Consultation reminder: {{ doc.title }}
   - DEV contains a BCC address; the BCC address is not committed

Migration behavior in draft PR #5:

- Notification definitions are part of the VitalAge configuration bootstrap.
- They are installed only after an Email Account named **Vital Age Clinic Admin** exists on the target site.
- Email Account passwords, mailbox credentials, BCC addresses, OAuth credentials, and other mail secrets remain environment-specific and are never stored in Git.

A fresh PROD site therefore requires the outbound Email Account to be configured manually before these Notification records can be recreated.

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

The 2026-09-29 supplemental role export and broad audit confirmed the exact VitalAge role set:

- **VitalAge Admin Master**
- **VitalAge Health Coordinator**
- **VitalAge Nurse**
- **VitalAge Nutrition Specialist**
- **VitalAge Physician**
- **VitalAge User Manager**

Role Profiles:

- **VitalAge Admin Master**
- **VitalAge Health Coordinator**
- **VitalAge Nurse**
- **VitalAge Nutrition Specialist**
- **VitalAge Physician**

There is no separate VitalAge User Manager Role Profile.

Role Profile membership:

- VitalAge Admin Master -> VitalAge Admin Master, Sales User, Sales Manager, Translator, VitalAge User Manager
- VitalAge Health Coordinator -> VitalAge Health Coordinator, Sales User
- VitalAge Nurse -> VitalAge Nurse, Sales User
- VitalAge Nutrition Specialist -> VitalAge Nutrition Specialist, Sales User
- VitalAge Physician -> VitalAge Physician, Sales User

## 12.1 Custom DocPerm audit

The initial migration export contained **38 Custom DocPerm** rows, while the broad 2026-09-29 audit found **66 Custom DocPerm rows on DEV versus 0 on clean PROD**.

Important conclusion:

> Filtering only to rows whose role is a VitalAge role is not sufficient to reproduce the effective customized permission model.

When Frappe permissions are customized, companion Custom DocPerm rows for standard roles can form part of the same effective permission matrix. Draft PR #5 therefore no longer uses the earlier incomplete 7-row Custom DocPerm fixture.

The migration bootstrap now applies the effective custom permission snapshot for intentionally customized DocTypes, including:

- VitalAge Physician access to Contact, CRM Lead, CRM Deal, CRM Task and FCRM Note
- VitalAge User Manager permissions for User, Role, Role Profile, Module Profile and User Type
- associated standard-role Custom DocPerm rows needed to preserve those customized matrices

ERPNext Item permission rows are intentionally not hard-coded because the CRM ERPNext integration creates them through its own setup logic.

These records contain configuration only; they do not copy User assignments or business/client data.

## 12.2 Repository-level hierarchy permissions

Files:

- crm/permissions/org_hierarchy.py
- crm/hooks.py
- crm/fcrm/doctype/fcrm_settings/fcrm_settings.json

FCRM Settings includes enable_sales_hierarchy.

When enabled:

- Lead and Deal read visibility is restricted by CRM Sales Hierarchy.
- Managers in the hierarchy can see records owned by/assigned to users in their subtree.
- Sales Users see own/assigned records.
- Administrator/System Manager bypass hierarchy restrictions.

Hooks:

- permission_query_conditions for CRM Lead and CRM Deal
- has_permission for CRM Lead and CRM Deal

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

However, the 2026-09-29 audit confirmed that the **ERPNext CRM integration itself is enabled on DEV** and is part of required site configuration.

Current DEV settings:

- ERPNext CRM Settings enabled = 1
- erpnext_company = Vital Age Clinic
- create_customer_on_status_change = 1
- deal_status = Monitoring
- is_erpnext_in_different_site = 0
- no ERPNext API key/secret is required for this same-site setup
- ERPNext CRM-related CRM Settings has Frappe CRM data synchronization enabled

Clean PROD had the ERPNext CRM integration disabled before migration work.

When the integration is enabled, CRM's own code creates system-generated records. The broad audit found examples including:

- CRM Product-erpnext_item_code
- Customer-crm_deal
- Item-crm_product_code
- Quotation-crm_deal
- Quotation-quotation_to-link_filters
- ERPNext Item permissions for Sales User / Sales Manager

These are **not VitalAge-authored customizations** and should not be copied as bespoke fixtures. Draft PR #5 applies the safe singleton settings and lets the CRM integration recreate these generated records through its own setup logic.

Relevant areas include:

- customer creation/synchronization
- Sales Order customer behavior
- Item/product synchronization
- product rate lookup
- ERPNext compatibility
- crm/fcrm/doctype/erpnext_crm_settings/erpnext_crm_settings.py

Do not remove these files casually: although product UI is not central to VitalAge operations, the ERPNext integration is enabled and its generated configuration is part of a correct site reconstruction.

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

- crm/install.py
- crm/patches.txt
- crm/patches/v1_0/add_task_participants_to_quick_entry.py
- crm/fcrm/vitalage_config.py — VitalAge site-configuration bootstrap introduced in draft PR #5
- crm/fixtures/role.json
- crm/fixtures/role_profile.json
- crm/fixtures/crm_deal_status.json
- crm/fixtures/crm_lead_status.json
- crm/fixtures/crm_lead_source.json

Important VitalAge migration behavior:

- Task Participants are inserted into existing CRM Task Quick Entry layouts via patch.
- Fresh installs include Participants in the default Task Quick Entry.
- existing sites are expected to migrate without manually rebuilding that layout.
- crm.fcrm.vitalage_config.apply_vitalage_site_config runs last in after_migrate so stock/upstream setup happens first and VitalAge values are applied afterward.
- Custom DocTypes, VitalAge Custom Fields, Property Setters, CRM Fields Layouts, CRM Form Scripts and Server Scripts are bootstrapped after migrate to avoid fresh-site fixture-order problems.
- VitalAge roles/Role Profiles and CRM statuses/sources use filtered fixtures.
- effective customized permissions are applied post-migrate rather than through the earlier incomplete role-only Custom DocPerm fixture.
- FCRM Settings are updated only for safe non-secret values.
- CRM/ERPNext singleton settings are reproduced without credentials.
- Administrator default views are created/updated without frappe.set_user impersonation:
  - Leads -> Group by Status
  - Deals -> Group by Owner
  - Tasks -> Calendar
- the bootstrap contains configuration only and must never include DEV Leads, Contacts, Deals, Tasks, Events, Communications, ToDos, passwords, API secrets, OAuth tokens, or other client/business data.

Any schema or Quick Entry customization introduced later should have both:

1. fresh-install behavior;
2. upgrade patch/bootstrap behavior.

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

**Migration update (2026-09-29):** these 11 Server Script bodies remain database-backed Frappe records at runtime, but draft PR #5 carries sanitized definitions in the VitalAge post-migrate bootstrap so a fresh site can recreate them without copying business data.

---

# 20. Site configuration / broad migration audit

## 20.1 2026-09-29 DEV-vs-clean-PROD broad audit

Before production migration, the same read-only configuration inventory was run on:

- DEV: vitalageclinic.frappe.cloud
- clean PROD: vitalage.frappe.cloud

The audit covered:

- every custom DocType
- Custom Field
- Property Setter
- Custom DocPerm
- Role / Role Profile
- Server Script / Client Script
- CRM Form Script
- CRM Fields Layout / CRM View Settings
- CRM Deal / Lead statuses and Lead sources
- Workflow-related records
- Notification
- Assignment Rule
- Workspace / Dashboard / Number Card
- Report / Print Format / Web Form
- Kanban / List View / Calendar View settings
- Email Template / Custom Translation
- Webhook
- User Permission
- FCRM Settings
- VitalAge CRM Settings
- ERPNext CRM Settings
- ERPNext CRM-related CRM Settings

Both final V3 exports completed with **Audit errors: 0**.

Key findings beyond the original migration export:

- two VitalAge Notifications were missed initially:
  - Client notification
  - Consultation Reminder - 7 Days
- DEV contained 66 Custom DocPerm rows versus 0 on clean PROD; the original migration export contained only 38
- complete VitalAge User Manager permissions were broader than the first role-only fixture
- CRM Organization-annual_revenue-permlevel was a real non-system-generated customization missing from the original export
- CRM data synchronization was enabled on DEV
- ERPNext CRM Settings were enabled/configured on DEV
- several DEV-only Custom Fields, Property Setters and Item permissions were confirmed as **system-generated ERPNext CRM integration artifacts**, not VitalAge-authored records
- some List View Settings differences were ordinary UI/system state and are not migrated as VitalAge configuration
- no unexpected VitalAge Workflows, Assignment Rules, Web Forms, Print Formats, Email Templates or custom Reports were identified by the broad audit

This audit materially changed draft PR #5 and is the reason the production migration package must not rely solely on the original narrower export.

## 20.2 Reproducible from Git after draft PR #5

The migration package is intended to reproduce:

- VitalAge custom DocTypes
- VitalAge Custom Fields
- VitalAge Property Setters, including CRM Organization annual-revenue permlevel
- effective customized DocPerm configuration
- VitalAge roles and Role Profiles
- Server Scripts
- CRM Form Scripts
- customized CRM Fields Layouts
- Deal statuses
- Lead statuses
- Lead sources
- VitalAge CRM Settings
- selected safe FCRM Settings
- CRM/ERPNext integration settings without secrets
- VitalAge Task Notifications once the required Email Account exists
- clean Administrator default views

## 20.3 Environment-specific configuration still handled separately

A repository clone is intentionally insufficient for secret/environment-specific infrastructure.

Preserve/configure separately:

- Google Calendar records and user mapping
- Google OAuth credentials/tokens
- Email Accounts and mailbox credentials
- Notification BCC addresses
- outbound mail configuration
- API keys/secrets
- exchange-provider access keys
- production integration-user credentials
- any other environment-specific secrets

Business/client data remains explicitly excluded from the migration package:

- Leads
- Contacts
- Deals / Client cases
- CRM Tasks
- Communications/emails
- Events
- ToDos
- other DEV operational/client records

The configuration-as-code improvement is now partially implemented by draft PR #5. Future site-level changes should be added to the bootstrap/fixtures at the same time they are introduced so DEV and PROD cannot silently drift.

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

