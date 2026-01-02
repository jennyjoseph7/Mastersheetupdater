# WhatsApp Webhook & Conversation Processing System

This document explains how we are registering WhatsApp webhook , how incoming messages are processed, how sessions are managed, and how credits, audit logs, and message performance tracking are handled.

## ✅ 1. Webhook Setup

Each WhatsApp provider must register a webhook using: webhook/whatsapp/<whatsapp_provider>

### Example:

webhook/whatsapp/meta
webhook/whatsapp/airtel
webhook/whatsapp/rml

Each provider has **only one webhook endpoint**.

---

## ✅ 2. Incoming Message Flow

Whenever a WhatsApp message is received from the provider, the system follows this pipeline:

### ✅ Step 1: Convert Payload
The raw provider-specific message is transformed into a **standard internal payload format** .

### ✅ Step 2: Session Management 


✅ 1. When the Message Is From a Campaign

        Only campaign messages will contain:

        campaign_id

        campaign_type (pre-sales / post-sales)

        dealership_id

✅ a) Validate or Create Person

    Look up the Person using the phone number.

    If found → reuse.

    If not → create a new Person.

✅ b) Validate or Create Session

    Look for an existing active session with:

        user_id

        conversation_id

        session_live = True

        status != "completed"

        application = "whatsapp"

    If such a session exists → reuse it.
    If not → create a new session.

✅ c) Get Lead Information & Update Session

Since campaigns contain campaign_id and campaign_type:

If campaign_type = pre_sales → call pre_sales model/API

If campaign_type = post_sales → call post_sales model/API

Use one or more filters:

campaign_id

dealership_id

phone_number

Extract lead_id and update the session with this lead_id.

✅ d) Dealership Credential Check

    If dealership_id = "dave" → skip credential validation.

    For all other dealerships → verify credentials using the appropriate model.
    - Look up a session using the **contact number**.
    - If an active session exists → continue the conversation.


### ✅ Step 3: Pass data to Conversation
Send a temporary data to conversation :

| Field        | Description                                      |
|--------------|--------------------------------------------------|
| `session_id` | Current/created session identifier               |
| `person_id`  | User’s mobile number                             |
| `campaign_id`| Campaign linked to user (if applicable)          |
| `dealership_id`|  Dealership id (if applicable)        |

## ✅ 4. Session Close

Update history in person_session model every 10 mins.

### 🔸 Auto Close After 24 Hours
If a session stays inactive for a full **day (24 hours)**:

- Automatically close the session  
- Mark it as complete  
- Stop all further messages  

---

## ✅ 5. Message Performance Tracking

The system captures detailed timestamps for every message travelling through the pipeline.  
These timestamps help measure delivery speed, processing quality, and system performance.

| **Metric** | **Description** |
|------------|------------------|
| **user_sent_time** | Timestamp when the user actually sends the message from WhatsApp. |
| **webhook_received_time** | Time when our server receives the webhook from the WhatsApp provider. |
| **process_start_time** | Timestamp marking when internal processing begins (payload normalization, session lookup, etc.). |
| **process_end_time** | Timestamp when internal processing finishes and the system is ready to generate a response. |
| **response_sent_starttimestamp** | Timestamp recorded **just before calling the WhatsApp send API**. |
| **response_sent_time** | Timestamp when the API call to send the message has completed (message handed off to WhatsApp provider). |
| **response_delivered_time** | Timestamp when we receive the **delivery status webhook** indicating the message was delivered to the user’s device. |

These values are stored in the **message model** under each person’s session.

---


--------------------------------------------------------

# Application Structure and Workflow

## 1. `communication_worker.py`
- Entry point for starting the communication worker.
- Loads communication configurations.
- Initializes the worker environment.

## 2. `communication_server.py`
- Runs the communication server.

## 3. `communication_configs.py`
- Initializes the Gryd service.
- Imports `grydConfig` and `i2ceHeaders` from `AppConfig`.
- Loads all configurations and environment variables.

> **Note:** After loading all modules, `base_connector_communication.py` is imported. Previously loaded tasks are reused instead of reloading.

## 4. `base_connector_communication.py`
- Main orchestration module for all communication channels.
- Manages multiple communication mediums, currently focusing on WhatsApp.

### WhatsApp
- Handles incoming messages via:
  - Webhook
  - Converse
- Supports multiple WhatsApp providers:
  1. Airtel
  2. Meta
  3. RML
  4. GupShup
  5. Concord (specific projects)

> **Note:** The system can also support other channels like Email through additional connectors.

## 5. `connector_whatsapp.py`
- Contains all Gryd-specific tasks related to WhatsApp communication.
- Acts as a bridge between the orchestration layer and provider-specific implementations.

## 6. `Whatsapp_connectors/`
- Contains provider-specific WhatsApp implementations.
- Example: Airtel connector for handling sending, receiving, and webhooks.
- Makes it easy to add new WhatsApp providers without modifying core modules.

## 7. Source Connectors
- Handles extraction of user data from external sources.
Currently implemented: Airtel.

> **Summary Workflow:**
> 1. Worker starts via `communication_worker.py` → loads configs → initializes environment.
> 2. Server runs via `communication_server.py` → handles requests/webhooks.
> 3. Messages are routed through `base_connector_communication.py` → WhatsApp messages are processed via `connector_whatsapp.py` → provider-specific logic in `Whatsapp_connectors`.
> 4. Source Connectors extract user data and trigger communications through the orchestration layer.



--------------------------------------------------------

# To start the worker - 

go to your environment variable 
run setup.sh
worker -m campaign/campaign_worker.py


------------------------------------------------------------------

# VOICEBOT -

We are using API from nikit.

--------------------------------------------------------------

# EMAIL -

We have mail_connectors which has AWS_SES_MAIL and SMTP_MAIL.

