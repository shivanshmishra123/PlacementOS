DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'placementos_app') THEN
        CREATE ROLE placementos_app LOGIN PASSWORD 'placementos_app_dev_password'
            NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'placementos_workflow') THEN
        CREATE ROLE placementos_workflow LOGIN PASSWORD 'placementos_workflow_dev_password'
            NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE placementos TO placementos_app;
GRANT USAGE ON SCHEMA public TO placementos_app;
GRANT CONNECT ON DATABASE placementos TO placementos_workflow;
CREATE SCHEMA IF NOT EXISTS workflow_checkpoints AUTHORIZATION placementos_workflow;
REVOKE ALL ON SCHEMA workflow_checkpoints FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE placementos IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO placementos_app;
ALTER DEFAULT PRIVILEGES FOR ROLE placementos IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO placementos_app;
