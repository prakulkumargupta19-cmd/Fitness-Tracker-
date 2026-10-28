-- Restrict student profile departments to the current programme list.
-- Preserve all existing profiles by replacing NULL or retired/unknown values
-- with a deterministic, per-student choice from the approved list first.
UPDATE student_profiles
SET department = (ARRAY[
    'BCA', 'BBA', 'BMS', 'HHA', 'BBA-HM', 'BMAGD', 'BBA-SM', 'BBA-GB',
    'BBA-E', 'BID', 'BFDM', 'BBA-ATA', 'BSC-DA', 'BBA-DM', 'BITAI', 'BAHSM'
])[1 + (MOD(ABS(HASHTEXT(user_id::TEXT)::BIGINT), 16))::INTEGER]
WHERE department IS NULL OR department NOT IN (
    'BCA', 'BBA', 'BMS', 'HHA', 'BBA-HM', 'BMAGD', 'BBA-SM', 'BBA-GB',
    'BBA-E', 'BID', 'BFDM', 'BBA-ATA', 'BSC-DA', 'BBA-DM', 'BITAI', 'BAHSM'
);

ALTER TABLE student_profiles
    DROP CONSTRAINT IF EXISTS chk_student_profiles_department;
ALTER TABLE student_profiles
    ADD CONSTRAINT chk_student_profiles_department
    CHECK (department IS NULL OR department IN (
        'BCA', 'BBA', 'BMS', 'HHA', 'BBA-HM', 'BMAGD', 'BBA-SM', 'BBA-GB',
        'BBA-E', 'BID', 'BFDM', 'BBA-ATA', 'BSC-DA', 'BBA-DM', 'BITAI', 'BAHSM'
    ));