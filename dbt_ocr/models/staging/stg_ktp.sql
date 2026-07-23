with source as (
    select * from {{ source('raw_ocr', 'ktp_records') }}
),

cleaned as (
    select
        id as record_id,
        file_path as source_file,
        trim(nik) as nik,
        upper(trim(nama)) as nama,
        trim(tempat_tgl_lahir) as tempat_tanggal_lahir,
        upper(trim(jenis_kelamin)) as jenis_kelamin,
        trim(alamat) as alamat,
        trim(rt_rw) as rt_rw,
        upper(trim(kel_desa)) as kelurahan_desa,
        upper(trim(kecamatan)) as kecamatan,
        upper(trim(agama)) as agama,
        upper(trim(status_perkawinan)) as status_perkawinan,
        upper(trim(pekerjaan)) as pekerjaan,
        upper(trim(kewarganegaraan)) as kewarganegaraan,
        trim(berlaku_hingga) as berlaku_hingga,
        processed_at
    from source
)

select * from cleaned
