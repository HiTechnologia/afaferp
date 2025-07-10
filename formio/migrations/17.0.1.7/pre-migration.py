def migrate(cr, version):
    cr.execute('ALTER TABLE formio_builder ADD COLUMN IF NOT EXISTS backend_submission_url_add_query_params_from character varying')
    cr.execute('ALTER TABLE formio_builder ADD COLUMN IF NOT EXISTS portal_submission_url_add_query_params_from character varying')
    cr.execute('ALTER TABLE formio_builder ADD COLUMN IF NOT EXISTS public_submission_url_add_query_params_from character varying')
    cr.execute('UPDATE formio_builder SET backend_submission_url_add_query_params_from = submission_url_add_query_params_from')
    cr.execute('UPDATE formio_builder SET portal_submission_url_add_query_params_from = submission_url_add_query_params_from')
    cr.execute('UPDATE formio_builder SET public_submission_url_add_query_params_from = submission_url_add_query_params_from')
