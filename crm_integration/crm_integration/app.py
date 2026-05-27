from connectors.google_docs_crm import GoogleDocsCRM

crm = GoogleDocsCRM("Ambal Sanganur Post-sales")


# ---------- TEST INSERT ----------
crm.post_pre_sales_lead({
    "workshop_city": "SANGANUR",
    "dealership_id": "4103-07",
    "VIN": "TEST123",
    "next_service_due": "2026-05-10",
    "person_name": "Priyanshul",
    "vehicle_model": "SWIFT",
    "reg_number": "TN01AB1234",
    "phone_number": "9999999999",
    "status": "NEW"
})


# ---------- TEST LIST ----------
data = crm.list_pre_sales_leads()
print("LIST:", data)


# ---------- TEST GET ----------
print(
    "GET:",
    crm.get_pre_sales_lead({
        "phone_number": "9999999999"
    })
)


# ---------- TEST PATCH ----------
print(
    "PATCH:",
    crm.patch_pre_sales_lead(
        {
            "phone_number": "9999999999"
        },
        "CONTACTED"
    )
)