with transactions as (
    select * from {{ ref('stg_transactions') }}
),

aggregated as (
    select
        source_file,
        sum(case when transaction_type = 'DB' then transaction_amount else 0 end) as total_debit,
        sum(case when transaction_type = 'CR' then transaction_amount else 0 end) as total_credit,
        count(*) as total_transaction_count,
        max(current_balance) as max_balance,
        min(current_balance) as min_balance
    from transactions
    group by source_file
)

select * from aggregated
