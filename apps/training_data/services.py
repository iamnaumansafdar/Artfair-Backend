from celery import group, chain
import environ
from huggingface_hub import login

from .models import MediaFile
from .tasks import (
    process_video_file,
    process_audio_file,
    process_audio_clips,
    process_subtitle_file,
    compile_training_dataset,
    clear_segment_files,
    download_user_files_from_remote,
    compile_dataset,
    push_to_hf,
)
from .utils import check_dataset_existence

class QueueProcessHelper(object):
    @classmethod
    def get_list_of_signatures(cls, files_by_owner):
        list_of_signatures = []
        for client_id, files in files_by_owner.items():
            # Download audio segment files of the user if the user has existing dataset on Hugging Face
            env = environ.Env()
            # Hugging Face authentication
            hf_token = env("HF_TOKEN")
            login(token=env("HF_TOKEN"))  # This will use HF_TOKEN environment variable
            dataset_name = f"{client_id}-Voice-Data"
            dataset_exists = check_dataset_existence(dataset_name, hf_token)
            chain_signature = None
            for file in files:
                chain_signature = cls.format_chain_signature(chain_signature, file, dataset_exists, client_id)
            if chain_signature is not None:
                chain_signature = chain_signature | compile_dataset.si(client_id) | push_to_hf.si(client_id) | clear_segment_files.si(client_id)
            list_of_signatures.append(chain_signature)
        return list_of_signatures


    @classmethod
    def format_chain_signature(cls, chain_signature, file, dataset_exists, client_id):
        tasks = []
        if dataset_exists and chain_signature is None:
            tasks = [download_user_files_from_remote.si(client_id)]
        tasks.append(process_subtitle_file.si(file["caption_file_id"]))
        if file["isAudioType"]:
            tasks.extend([
                process_audio_file.si(file["file_id"]),
                process_audio_clips.si(file["file_id"]),
                compile_training_dataset.si(client_id, file["file_id"]),
            ])
        else:
            tasks.extend([
                process_video_file.si(file["file_id"]),
                process_audio_clips.si(file["file_id"]),
                compile_training_dataset.si(client_id, file["file_id"]),
            ])

        # Create a new chain from the tasks list
        new_chain = chain(*tasks)

        # Concatenate to the existing chain if it exists; otherwise, start a new one
        if chain_signature is None:
            chain_signature = new_chain
        else:
            chain_signature = chain_signature | new_chain

        return chain_signature


class QueueProcessService(object):

    @classmethod
    def queue_media_to_training_data(cls, media_files):
        # files_by_owner key: owner_id, value: list of file_info dictionary which is used to create chain signature of all files owned by the owner
        files_by_owner = {}
        for file in media_files:
            # if a caption file is accidently selected in the admin panel, ignore it
            if file.file_type == "ass" or file.processing_status == "completed":
                continue
            owner_id = file.owner.id
            caption_file = file.caption_file
            isAudioType = file.file_type == "audio"
            isVideoType = file.file_type == "video"

            if not caption_file:
                # Skip if there's no caption file
                continue
            # Tasks for processing caption file into .csv file and video file into audio file 
            process_csv_task = process_subtitle_file.si(caption_file.id)
            file_info = {
                "caption_file_id": caption_file.id,
                "file_id": file.id,
                "owner_id": owner_id,
                "isAudioType": isAudioType,
            }
            files_by_owner.setdefault(owner_id, []).append(file_info)

            if isAudioType:
                chain(
                    process_csv_task,
                    process_audio_file.si(file.id),
                    process_audio_clips.si(file.id),
                    # compile_training_dataset.si(owner_id, file.id), clear_segment_files.si(file.id)
                    push_to_hf.si(file.id)
                ).apply_async()
            elif isVideoType:
                chain(
                    process_csv_task,
                    process_video_file.si(file.id),
                    process_audio_file.si(file.id),
                    process_audio_clips.si(file.id),
                    push_to_hf.si(file.id)
                    # compile_training_dataset.si(owner_id, file.id), clear_segment_files.si(owner_id)
                ).apply_async()

        # list_of_signatures = QueueProcessHelper.get_list_of_signatures(files_by_owner)
        # group(list_of_signatures).apply_async()
