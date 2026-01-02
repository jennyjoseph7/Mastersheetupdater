import os,json
from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys
import pdfkit
sys.path.insert(0, dirname(dirname(abspath(__file__))))
from communication.connectors.communication_helpers import *
from communication.connectors.mail_connectors.source_connector import MailSourceFactory
from config import AUTOCRM_COMMUNICATION_SERVICE_NAME,EMAIL_PROVIDER_NAME,EMAIL_SENDER_NAME,AUTOCRM_APP_ENTERPRISE_ID
from gryd_worker import gryd, gryd_db_helper as db, gryd_helpers as hp
gryd.SERVICE = AUTOCRM_COMMUNICATION_SERVICE_NAME
gryd.set_queue_manager()
logger = gryd.hp.get_logger(gryd.SERVICE)

# PDF generation
def make_pdf(html: str, path: str) -> str | None:
    try:
        output_path = Path(path)
        pdfkit.from_string(html, str(output_path))
        logger.info(" PDF generated at: %s", output_path)
        return str(output_path)
    except Exception as e:
        logger.error(" Error generating PDF: %s", e)
        hp.print_error()
        return None
@gryd.is_a_task(function_name="gryd_start_mail")
def gryd_start_mail(
    to_email,
    subject,
    html,
    sender_email,
    view_type,
    enterprise_id=None,
    pdf=False,
    gryd_hook=None,
    text=None,
    pdf_html=None,
    provider=None,
    **kwargs
):
    files = kwargs.pop("files", [])
    delete_after_send = kwargs.pop("delete_after_send", False)
    send_files = {}
    opened_files = {}
    download_folder = "static/uploads/email_files_dlows"
    os.makedirs(download_folder, exist_ok=True)

    try:
        if pdf:
            filename = f"{hp.normalize_join(subject, hp.make_uuid3())}.pdf"
            with NamedTemporaryFile(delete=False) as tmp_file:
                pdf_path = tmp_file.name
            pdf_result = make_pdf(pdf_html or html, pdf_path)
            if pdf_result:
                files.append((pdf_result, filename))

                
        for file in files:
            try:
                if isinstance(file, (tuple, list)):
                    file_path = file[0]
                    file_name = file[1] if len(file) > 1 else None
                else:
                    file_path = file
                    file_name = None

                if file_path.startswith(('http://', 'https://')):
                    # URL: download and save to folder
                    logger.info(f"Downloading File from URL: {file_path}")
                    response = requests.get(file_path)
                    response.raise_for_status()

                    # Determine filename
                    file_name = file_name or os.path.basename(urlparse(file_path).path)
                    saved_path = os.path.join(download_folder, file_name)

                    # Write content to file
                    with open(saved_path, 'wb') as f:
                        f.write(response.content)

                    file_obj = open(saved_path, 'rb') 
                    need_delete = delete_after_send  

                else:
                    # Local file
                    if file_path and os.path.isfile(file_path):
                        file_obj = open(file_path, 'rb')
                        file_name = file_name or os.path.basename(file_path)
                        need_delete = delete_after_send
                        saved_path = file_path
                    else:
                        raise FileNotFoundError(f"File not found: {file_path}")

                opened_files[saved_path] = (file_obj, need_delete)
                send_files[saved_path] = ('attachment', (file_name, file_obj))
                logger.info("Prepared file: %s", file_name)

            except Exception as file_err:
                logger.error("Error attaching file %s: %s", file_path, file_err)

        
        provider = provider or '__default__'
        mail_sender= MailSourceFactory.mail_sender(provider,gryd_hook=gryd_hook, credentials=kwargs.get('credentials'))
        logger.info("Sending email to: %s | Subject: %s | Via: %s", to_email, subject, provider)

        
        response = mail_sender.sendMail(
            to=to_email,
            subject=subject,
            enterprise_id=enterprise_id,
            files=list(send_files.values()),
            sender=sender_email,
            text=text,
            html=html,
            view_type=view_type,
            **kwargs
        )
        logger.info(" Email sent. Response: %s", response)
        
        # TODO: call contact_status 

    except Exception as e:
        logger.error("Failed to send email: %s", e)
        hp.print_error()
        response = {"error": str(e)}

    finally:
    
        for file_path, (file_obj,need_delete) in opened_files.items():
            try:
                file_obj.close()
                if delete_after_send:
                    os.remove(file_path)
                    logger.info("Deleted file: %s", file_path)
            except Exception as cleanup_err:
                logger.error("Error cleaning up file %s: %s", file_path, cleanup_err)

    return {
        "provider": provider,
        "to": to_email,
        "attachments": list(send_files.keys()),
        "response": response
    }

def send_email_otp(*args, **kwargs):
    """
    Sends OTP email using configured email provider.
    """

    to_email=kwargs.get("to_email")
    otp=kwargs.get("otp")
    message=kwargs.get("message")
    if not to_email or not otp:
        raise ValueError("to_email and otp are required")
    
    try:
        if not message:
            message = f"Your OTP for Login is {otp}"

        return gryd_start_mail(to_email, "OTP Verification", message, EMAIL_SENDER_NAME, "transaction", AUTOCRM_APP_ENTERPRISE_ID, pdf=False, provider=EMAIL_PROVIDER_NAME)

    except Exception as e:
        logger.info(f"Failed to send OTP email | to={to_email} | error={str(e)}")

if __name__=="__main__":
    gryd_start_mail(
        ['nitesh@iamdave.ai','ntssahu485@gmail.com'], 'test','<p> This is a test email for AWS </p>', 'DaveAI Test <info@iamdave.ai>', 'transaction',
        pdf=False,
        provider='AwsSender', 
        # cc = "ntssahu485@gmail.com",
        files=[
            ["https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/bde3c8c1-5053-47cf-8b2a-fbe8c1b8dc4f-68e8b8e4_SwiftTechnicalSpecification.pdf"]
        ],
        enterprise_id="test1",
    )