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


