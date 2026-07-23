with source as (
    select * from {{ source('raw_ocr', 'bank_transactions') }}
),

renamed as (
    select
        id as transaction_id,
        file_path as source_file,
        date as raw_transaction_date,
        trim(description) as transaction_description,
        coalesce(amount, 0.0)::decimal(15, 2) as transaction_amount,
        upper(trim(type)) as transaction_type, -- DB (Debit) or CR (Credit)
        coalesce(balance, 0.0)::decimal(15, 2) as current_balance,
        processed_at
    from source
)

select * from renamed
