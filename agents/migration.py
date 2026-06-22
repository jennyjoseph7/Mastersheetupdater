from generic_template_migrator import UniversalTemplateMigrator

migrator = UniversalTemplateMigrator(
    communication_credential_id="rml-whatsapp_chat-919187238014"
)

result = migrator.migrate()
print(result)