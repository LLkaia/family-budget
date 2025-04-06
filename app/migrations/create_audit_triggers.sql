--
CREATE OR REPLACE FUNCTION log_transaction_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO auditlog(table_name, operation, record_id, new_data)
        VALUES (TG_TABLE_NAME, TG_OP, NEW.id, to_jsonb(NEW));
        RETURN NEW;

    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO auditlog(table_name, operation, record_id, old_data, new_data)
        VALUES (TG_TABLE_NAME, TG_OP, NEW.id, to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;

    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO auditlog(table_name, operation, record_id, old_data)
        VALUES (TG_TABLE_NAME, TG_OP, OLD.id, to_jsonb(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
--
DROP TRIGGER IF EXISTS trigger_transaction_audit ON transaction;
--
CREATE TRIGGER trigger_transaction_audit
AFTER INSERT OR UPDATE OR DELETE ON transaction
FOR EACH ROW
EXECUTE FUNCTION log_transaction_changes();
--
DROP TRIGGER IF EXISTS trigger_account_transaction_audit ON accounttransaction;
--
CREATE TRIGGER trigger_account_transaction_audit
AFTER INSERT OR UPDATE OR DELETE ON accounttransaction
FOR EACH ROW
EXECUTE FUNCTION log_transaction_changes();
--
