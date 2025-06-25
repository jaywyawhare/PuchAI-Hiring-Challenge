#!/bin/bash

echo "🚀 Starting complete setup..."

# Make scripts executable
chmod +x setup_docker.sh

# Step 1: Setup Docker
echo "Step 1: Setting up Docker..."
./setup_docker.sh

# Step 2: Install Python dependencies with better error handling
echo "Step 2: Installing Python dependencies..."
echo "📦 Installing PyTorch first..."
pip install torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu

echo "📦 Installing other dependencies..."
pip install -r requirements.txt

# Step 3: Setup database
echo "Step 3: Setting up database..."
python setup_database.py

# Step 4: Import schemes data
echo "Step 4: Importing schemes data..."
python import_schemes.py

# Step 5: Create embeddings (using simplified version)
echo "Step 5: Creating vector embeddings..."
python create_embeddings_simple.py

echo "🎉 Complete setup finished!"
echo "📊 You can now query your schemes database!"
echo ""
echo "🔍 To test the database:"
echo "  sudo docker exec -it warpspeed-postgres psql -d whatsapp_bot -c 'SELECT COUNT(*) FROM schemes;'"
echo "  sudo docker exec -it warpspeed-postgres psql -d whatsapp_bot -c 'SELECT COUNT(*) FROM scheme_embeddings;'"
