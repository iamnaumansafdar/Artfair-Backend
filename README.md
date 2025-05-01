<div align="center">
    <img src="https://raw.githubusercontent.com/wilfredinni/django-starter-template/refs/heads/main/static/logo.png" data-canonical-src="/logo.png" width="130" height="130" />

# Django starter template

A comprehensive and easy-to-use starting point for your new API with **Django** and **DRF**.

[![Test Status](https://github.com/wilfredinni/django-starter-template/actions/workflows/test.yml/badge.svg)](https://github.com/wilfredinni/django-starter-template/actions/workflows/test.yml)
[![CodeQL Status](https://github.com/wilfredinni/django-starter-template/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/wilfredinni/django-starter-template/actions/workflows/github-code-scanning/codeql)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/wilfredinni/django-starter-template?tab=MIT-1-ov-file#readme)
</div>

## Key features

### Project Name: ArtFair AI Core API

ArtFair AI Core API is a Django-based application that enables rights holders (e.g., YouTube channels, podcasts, labels) to upload video and audio files along with subtitle files. It processes these media assets through a Celery-powered pipeline to extract audio, segment clips, generate training metadata, and assemble Hugging Face datasets for ASR (Automatic Speech Recognition) fine-tuning. The system supports both local file storage and AWS S3 integration for scalable media management.


This template includes battle-tested features for building secure, scalable, and maintainable APIs

### Core Features
- Media Upload & Management – Upload video, audio, and subtitle (.ass) files via REST API or Uppy-powered admin panel.

- File Linking – Associate subtitle files to their source media for synchronized processing.

- Processing Pipeline – Convert video to audio, transcode audio, segment into clips, and compile CSV metadata.

- Hugging Face Integration – Automatically upload compiled datasets for each rights owner channel.

- Speaker Extraction – Parse and manage speaker identities from subtitle data.

- Download URLs – Generate presigned S3 URLs or local URLs for media downloads.

- Analytics & Licensing – (Planned) Extend for licensing data consumption and usage analytics.


### Architecture
- Django REST Framework: Core API endpoints, serializers, and viewsets.

- Celery with Redis: Background task processing for media pipelines (video → audio → segments → dataset).

- PostgreSQL: Primary relational database for media metadata, channels, and speakers.

- AWS S3: Optional remote storage for media and static assets (REMOTE_STATIC_FILES=True).

- Uppy: Client-side file uploader in the Django admin UI for drag-and-drop uploads.

- Hugging Face: Destination for compiled ASR training datasets per channel

### Database & Caching
- 💿 Pre-configured [PostgreSQL](https://www.postgresql.org/) database
- 📦 [Redis](https://redis.io/) caching system
- 🗄️ BaseModel with `created_at` and `updated_at` fields
- 🗑️ Optional SoftDeleteBaseModel for soft deletions

### Authentication & Users
- 🔒 Complete auth system using [Knox](https://jazzband.github.io/django-rest-knox/)
- 🙋 Extended user model with email-based authentication

### Task Management
- ⏳ [Celery](https://docs.celeryq.dev/en/stable/) for async tasks with BaseTaskWithRetry
- 🗃️ Task results storage with django_celery_results
- 📅 Task scheduling through django_celery_beat

### Development Tools
- 🧪 Testing with [Pytest](https://docs.pytest.org/en/stable/)
- ⚡ Interactive development using Jupyter Notebooks
- 🐞 Debugging with Django Debug Toolbar
- 🔧 Code quality tools: [Black](https://black.readthedocs.io/), [Flake8](https://flake8.pycqa.org/)
- 👨‍💻 [VS Code](https://code.visualstudio.com/) with [Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers)

### Additional Features
- 🔽 Advanced filtering with django-filter
- 🧩 Extended functionality with Django Extensions


## Requirements

- 💻 VS Code
- 🐋 Docker
- 🐳 Docker Compose


## Commands

This template comes with some shortcuts so you don't have to memorize how to start the workers:

- `poetry run worker`: to start a new Celery worker.
- `poetry run beat`: to start your periodic tasks.

You can also use:

- `poetry run server` instead of `python manage.py runserver`
- `poetry run makemigrations` instead of `python manage.py makemigrations`
- `poetry run migrate` instead of `python manage.py migrate`
- `poetry run create_dev_env` to create a development `.env` file


## Celery Task Commands

- `celery -A conf worker --loglevel=info`



# Create the Virtual Environment

poetry install

poetry shell
