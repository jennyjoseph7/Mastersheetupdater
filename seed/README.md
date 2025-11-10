# Seed Data Documentation

This directory contains seed data for the AutoBot Agents project. The seed data follows the entity-relationship diagram and maintains all relationships between entities.

## Data Structure

The seed data is organized by entity type, with each JSON file containing an array of records for that entity. The data follows the model sequence defined in `data/model_sequence.json`.

## Entity Files

### Foundational Entities
- **oem.json** - Original Equipment Manufacturers (Maruti Suzuki, Hyundai, Tata Motors)
- **region.json** - Geographic regions (North, South, East, West India)
- **dealer_group.json** - Dealer group organizations
- **communication_provider.json** - Communication service providers (WhatsApp, Twilio, SendGrid, Intercom)

### Product Hierarchy
- **brand.json** - Vehicle brands (NEXA, Arena, Hyundai)
- **vehicle_model.json** - Vehicle models (Baleno, Fronx, Grand Vitara, Invicto, Swift, Verna)
- **model_year.json** - Model year variations
- **variant.json** - Vehicle variants with specifications
- **color.json** - Available vehicle colors
- **feature.json** - Vehicle features (SmartPlay Pro+, Cruise Control, Airbags, etc.)
- **variant_feature.json** - Features available in specific variants
- **variant_colour.json** - Color options for specific variants

### Dealership Entities
- **dealership.json** - Dealership locations
- **showroom.json** - Showroom locations
- **workshop.json** - Service workshop locations
- **buyback_center.json** - Vehicle buyback centers

### Customer Entities
- **person.json** - Customer/person records
- **vehicle.json** - Vehicle records
- **person_vehicle.json** - Person-vehicle relationships

### Campaign Entities
- **dealership_campaign.json** - Dealership-level campaigns
- **pre_sales_campaign.json** - Pre-sales campaigns
- **post_sales_campaign.json** - Post-sales campaigns
- **campaign_workflow.json** - Campaign workflow configurations
- **dealership_lead.json** - Dealership leads
- **pre_sales_lead.json** - Pre-sales leads
- **post_sales_lead.json** - Post-sales leads

### Interaction Entities
- **showroom_visit.json** - Showroom visit records
- **service_visit.json** - Service/workshop visit records
- **review.json** - Showroom visit reviews
- **feedback.json** - Service visit feedback
- **messsage.json** - Message records
- **message_event.json** - Message delivery events
- **session.json** - Communication sessions

### Supporting Entities
- **human_agent.json** - Human agent/employee records
- **template.json** - Message templates
- **communication_credential.json** - Communication API credentials
- **billing.json** - Billing records
- **billing_report.json** - Billing reports
- **contact_status.json** - Contact status tracking
- **document.json** - Document records (brochures, specifications)
- **paragraph.json** - Content paragraphs
- **session_data_cache.json** - Session data cache

## Data Relationships

The seed data maintains the following key relationships:

1. **OEM → Brand → Vehicle Model → Model Year → Variant**
2. **Dealer Group → Dealership → Showroom/Workshop**
3. **Person → Person_Vehicle → Vehicle**
4. **Campaign → Campaign Workflow → Leads**
5. **Dealership → Campaign → Leads**
6. **Person → Session → Message → Message Event**
7. **Showroom Visit → Review**
8. **Service Visit → Feedback**

## Usage

To load the seed data into your database, you should process the files in the order specified in `data/model_sequence.json`:

1. oem
2. dealer_group
3. person
4. communication_provider
5. document
6. region
7. session
8. session_data_cache
9. brand
10. model (vehicle_model)
11. model_year
12. vehicle_model
13. variant
14. color
15. feature
16. variant_feature
17. variant_color
18. vehicle
19. dealership
20. showroom
21. workshop
22. buyback_center
23. dealership_campaign
24. pre_sales_campaign
25. post_sales_campaign
26. campaign_workflow
27. dealership_idea
28. dealership_lead
29. pre_sales_lead
30. post_sales_lead
31. message
32. template
33. showroom_visit
34. workshop_visit (service_visit)
35. human_agent
36. feedback
37. review
38. paragraph
39. communication_credential
40. billing
41. billing_report
42. contact_status
43. message_event

## Notes

- All timestamps are in Unix epoch format (seconds since January 1, 1970)
- IDs follow a consistent naming pattern for easy reference
- Foreign key relationships are maintained through ID references
- The data includes realistic Indian automotive dealership scenarios
- Phone numbers follow Indian format (+91 prefix)
- Addresses and locations are based on major Indian cities

## Sample Data Highlights

- **2 Dealerships**: NEXA Delhi South, NEXA Mumbai West
- **3 Customers**: Anita Menon, Rajesh Kumar, Priya Sharma
- **3 Vehicles**: Baleno, Fronx, Baleno (different variants)
- **Multiple Campaigns**: Pre-sales and post-sales campaigns
- **Interaction Records**: Visits, reviews, feedback, messages, sessions

