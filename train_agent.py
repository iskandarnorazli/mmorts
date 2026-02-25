import pyarrow as pa
import pyarrow.flight as flight
from adbc_driver_flightsql import dbapi
import base64

def run_training():
    print("==========================================")
    print("   🚂 AwanDB GraalVM Training Sequence    ")
    print("==========================================\n")

    auth_str = base64.b64encode(b"admin:admin").decode("utf-8")
    basic_auth_header = f"Basic {auth_str}"

    # ---------------------------------------------------------
    # PHASE 1: STANDARD FLIGHT SQL (Testing JSqlParser Reflection)
    # ---------------------------------------------------------
    print("-> Phase 1: Connecting via ADBC Flight SQL...")
    conn = dbapi.connect(
        "grpc://localhost:3000",
        db_kwargs={
            "adbc.flight.sql.rpc.call_header.Authorization": basic_auth_header,
        }
    )
    cursor = conn.cursor()

    # [FIX] Cleanup any ghost tables from previous crashed runs
    print("   [+] Cleaning up old state...")
    try:
        cursor.execute("DROP TABLE graal_test")
        cursor.fetchall()
    except Exception:
        pass # If it fails, the table didn't exist, which is fine!

    print("   [+] Testing DDL (CREATE TABLE)...")
    cursor.execute("CREATE TABLE graal_test (id INT, value INT)")
    print(f"       Result: {cursor.fetchall()}")

    print("   [+] Testing DML (INSERT & UPDATE)...")
    cursor.execute("INSERT INTO graal_test VALUES (1, 100)")
    print(f"       Result: {cursor.fetchall()}")
    
    cursor.execute("INSERT INTO graal_test VALUES (2, 200)")
    print(f"       Result: {cursor.fetchall()}")
    
    cursor.execute("INSERT INTO graal_test VALUES (3, 300)")
    print(f"       Result: {cursor.fetchall()}")
    
    cursor.execute("UPDATE graal_test SET value = 999 WHERE id = 1")
    print(f"       Result: {cursor.fetchall()}")

    print("   [+] Testing Complex Query (Aggregations)...")
    cursor.execute("SELECT COUNT(*) AS total, SUM(value) AS total_val FROM graal_test WHERE value > 150")
    print(f"       Result: {cursor.fetchall()}")

    print("   [+] Testing DDL (DROP TABLE)...")
    cursor.execute("DROP TABLE graal_test")
    print(f"       Result: {cursor.fetchall()}")
    conn.close()

    # ---------------------------------------------------------
    # PHASE 2: RAW ARROW STREAM (Testing Zero-Copy JNI Buffer)
    # ---------------------------------------------------------
    print("\n-> Phase 2: Connecting via Raw Flight RPC...")
    client = flight.FlightClient("grpc://localhost:3000")
    
    options = flight.FlightCallOptions(headers=[(b"authorization", basic_auth_header.encode("utf-8"))])

    descriptor = flight.FlightDescriptor.for_path("leaderboard")
    schema = pa.schema([('val', pa.int32())])
    writer, _ = client.do_put(descriptor, schema, options=options)
    
    print("   [+] Blasting Binary DoPut Stream...")
    batch = pa.RecordBatch.from_arrays([pa.array([10, 20, 30, 40, 50], type=pa.int32())], schema=schema)
    writer.write_batch(batch)
    writer.close()
    
    print("\n✅ Training Sequence Complete! You may now kill the AwanDB Server.")

if __name__ == "__main__":
    run_training()