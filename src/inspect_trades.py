import duckdb

con = duckdb.connect()
print("=== exectype and ordstatus breakdown ===")
print(con.sql("""
    SELECT exectype, ordstatus, count(*) as count
    FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-2018-03-01-2018-12-31.csv'
    GROUP BY exectype, ordstatus
""").df().to_string())

print("\n=== Check unique trade identifiers (execid vs trdmatchid) ===")
print(con.sql("""
    SELECT 
        count(*) as total_rows,
        count(distinct execid) as distinct_execid,
        count(distinct trdmatchid) as distinct_trdmatchid
    FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-2018-03-01-2018-12-31.csv'
""").df().to_string())

print("\n=== First few trades sorted chronologically on 2018-03-05 ===")
print(con.sql("""
    SELECT 
        transacttime, side, ordtype, ordstatus, lastqty, lastpx, cumqty, leavesqty
    FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-2018-03-01-2018-12-31.csv'
    WHERE date = '2018-03-05'
    ORDER BY CAST(transacttime AS TIMESTAMP) ASC
    LIMIT 25
""").df().to_string())
