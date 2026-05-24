@echo off
echo ===================================================
echo Setting up Hugging Face Docker Space...
echo ===================================================

echo.
echo [1/3] Creating requirements.txt...
echo fastapi > requirements.txt
echo uvicorn[standard] >> requirements.txt

echo.
echo [2/3] Creating app.py...
echo from fastapi import FastAPI > app.py
echo. >> app.py
echo app = FastAPI() >> app.py
echo. >> app.py
echo @app.get("/") >> app.py
echo def greet_json(): >> app.py
echo     return {"Hello": "World!"} >> app.py

echo.
echo [3/3] Creating Dockerfile...
echo FROM python:3.9 > Dockerfile
echo RUN useradd -m -u 1000 user >> Dockerfile
echo USER user >> Dockerfile
echo ENV PATH="/home/user/.local/bin:$PATH" >> Dockerfile
echo WORKDIR /app >> Dockerfile
echo COPY --chown=user ./requirements.txt requirements.txt >> Dockerfile
echo RUN pip install --no-cache-dir --upgrade -r requirements.txt >> Dockerfile
echo COPY --chown=user . /app >> Dockerfile
echo CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"] >> Dockerfile

echo.
echo ===================================================
echo Files created successfully.
echo Now configuring Git and pushing to Hugging Face...
echo ===================================================

git init
git remote add origin https://huggingface.co/spaces/saravanahuggingface/chat
git add requirements.txt app.py Dockerfile
git commit -m "Add application file"
git branch -M main

echo.
echo Pushing to Hugging Face Space (you may be prompted for your Hugging Face Access Token)...
git push -u origin main --force

echo.
echo ===================================================
echo Done! Your Space should be building now.
echo Check it out at: https://huggingface.co/spaces/saravanahuggingface/chat
echo ===================================================
pause
