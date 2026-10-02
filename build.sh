#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
# Builds faiss_index/ (and downloads the ONNX models into .model_cache/) unless the manifest is current
python manage.py build_rag_index
