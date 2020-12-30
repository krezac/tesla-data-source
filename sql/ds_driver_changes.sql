CREATE TABLE IF NOT EXISTS ds_driver_changes
(
	id serial not null,
	date_from timestamp without time zone not null,
	date_to timestamp without time zone null,
	name varchar(255)
);

alter table ds_driver_changes owner to teslamate;

CREATE SEQUENCE IF NOT EXISTS ds_driver_changes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE ds_driver_changes_id_seq OWNER TO teslamate;

ALTER SEQUENCE ds_driver_changes_id_seq OWNED BY ds_driver_changes.id;

ALTER TABLE ONLY ds_driver_changes ALTER COLUMN id SET DEFAULT nextval('ds_driver_changes_id_seq'::regclass);

ALTER TABLE ONLY ds_driver_changes
    ADD CONSTRAINT ds_driver_changes_pkey PRIMARY KEY (id);
