# from gryd_worker import gryd

# # -------------------- GRYD CONFIG --------------------
# gryd.SERVICE = "spark"

# gryd.set_queue_manager(config={
#     "broker_type": "sqs",
#     "timeout": 10
# })

# if __name__ == "__main__":
#     # Frontend-provided image URL
#     input_image_url = (
#         "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/8588beef-28e7-46a9-983f-868941d19657-6985f3ba_upload.jpg"
#     )

#     # Prompt constructed from your business params
#     prompt = (
#         "black window car "
#     )

#     kwargs = {
#         "input_image_url": input_image_url,
#         "prompt": prompt,
#         "number_of_images": 1
#     }

#     # Create async task
#     gryd.create_async_task(
#         service="spark",
#         function_name="comfy_image_generation_task",
#         kwargs=kwargs
#     )



from gryd_worker import gryd

# -------------------- GRYD CONFIG --------------------
gryd.SERVICE = "spark"

gryd.set_queue_manager(config={
    "broker_type": "sqs",
    "timeout": 10
})

if __name__ == "__main__":
    input_image_url = (
        "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp"
    )

    prompt = "black window car"

    kwargs = {
        "input_image_url": input_image_url,
        "prompt": prompt,
        "number_of_images": 2
    }

    gryd.create_async_task(
        service="spark",
        function_name="comfy_image_generation_task",
        kwargs=kwargs
    )
