with source as (
    select * from "jaffle_shop"."main"."raw_payments"

),

renamed as (

    select
        id as payment_id,
        order_id,
        payment_method,

        -- `amount` is currently stored in cents, so we convert it to dollars
        amount

    from source

)

select * from renamed