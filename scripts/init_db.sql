-- Database initialization script
-- This script runs when PostgreSQL container is first created

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'Asia/Seoul';

-- Create indexes for common queries (will be created by Alembic, but useful for reference)
-- These are examples and should be created through Alembic migrations

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE ocrdb TO ocruser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ocruser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ocruser;

-- Display info
SELECT 'Database initialized successfully!' as status;
SELECT version() as postgresql_version;
