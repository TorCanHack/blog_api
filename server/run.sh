if [ -f .env ]; then
    echo "Loading environment from .env file"
    export $(cat .env | grep -v '^#' | xargs)
fi 

if [ "$1" = "install" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    exit 0
fi

if [ "$1" = "prod" ]; then 
    echo "Starting the API server in production mode..."
    gunicorn --workers=4 --threads=2 --bind=0.0.0.0:${PORT:-5000} app:app
else
    echo "Starting the API server in development mode..."
    python app.py
fi