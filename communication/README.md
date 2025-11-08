<!-- webhook - webhook/whatsapp/<whatsapp_provider> (only one webhook for each whatsapp provider) - I will register the webhook this way 

once we get any incoming message from webhook we need to 

first convert to standard payload format.
check for credits. 

check if existing session exists - with contact number , if not then check contact status model , the last message sent to this person during the interval of 1 day (check the attribute) if it exists pick the campaign id - last campaign 

Then send these 3 attributes in temp data to conversation.
a) session_id,
b) person_id (user's number),
c) campaign_id (if its from campaign)


inactive - 10 mins just update history calls agent etc. 
close session after a day.


audit logs for how much we are spending and reduce the credits based on the messages we get and send. 



track initial process time, response time and sent timestamp , update in person session in message model how long it took for a message. 
 -->



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

### ✅ Step 2: Credit Check
Before sending any response or continuing processing, validate that the system has **sufficient credits**.

### ✅ Step 3: Check for Existing Session
- Look up a session using the **contact number**.
- If an active session exists → continue the conversation.

If no session exists:
1. Check the **ContactStatus** model  
2. Identify the **last message sent within 1 day**  
3. If found → extract its associated `campaign_id`  


### ✅ Step 4: Pass data to Conversation
Send a temporary data to conversation :

| Field        | Description                                      |
|--------------|--------------------------------------------------|
| `session_id` | Current/created session identifier               |
| `person_id`  | User’s mobile number                             |
| `campaign_id`| Campaign linked to user (if applicable)          |

---

## ✅ 3. Session Management

Update history in person_session model every 10 mins.

### 🔸 Auto Close After 24 Hours
If a session stays inactive for a full **day (24 hours)**:

- Automatically close the session  
- Mark it as complete  
- Stop all further messages  

---

## ✅ 4. Credits & Audit Logging

The system logs and deducts credits for:

✅ Incoming messages  
✅ Outgoing messages  
✅ Session-linked communication  

---

## ✅ 5. Message Performance Tracking

The system tracks detailed performance metrics for every message:

| Metric                      | Meaning                                  |
|-----------------------------|-------------------------------------------|
| **Processing time**         | Time from receiving to parsing            |
| **Response generation time**| Time taken by conversation engine         |
| **Message sent timestamp**  | Actual timestamp of outbound delivery     |

These values are stored in the **message model** under each person’s session.

---


## Campaign 

When a message is sent as part of a campaign, the system updates five tracking fields in the ContactStatus model. If the next incoming WhatsApp message is received from the same person_id (mobile number), the system identifies it as a campaign reply and automatically creates a new PersonSession for that user.

