# tesla-data-source
Present data from Tesla API scrapers like Teslamate or Tesla Logger (TODO) to web. Lap analyzer...

## Instalation

### SQL
You need to execute the sql/ds_driver_changes.sql script first to create
driver change table. Without that, it won't work properly. Always refer the file 
for most recent version of the script.

```sql
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
```

### Docker-compose
Add it as new service to your Teslamate docker-compose.yml
```yaml
  datasource:
    image: krezac/tesla-data-source:latest
    restart: always
    depends_on:
      - database
    environment:
      - TM_DB_USER=${TM_DB_USER}
      - TM_DB_PASS=${TM_DB_PASS}
      - TM_DB_NAME=${TM_DB_NAME}
      - TM_DB_HOST=database
      - POST_CONFIG_TOKEN="abcdefgh"
      - FIO_API_TOKEN="abcdefgh"
    labels:
      - 'traefik.enable=true'
      - "traefik.http.middlewares.tm-datasource-redirect.redirectscheme.scheme=https"
      - "traefik.http.routers.tm-datasource-insecure.rule=Host(`sub1.example.com`)"
      - "traefik.http.routers.tm-datasource-insecure.middlewares=tm-datasource-redirect"
      - "traefik.http.routers.tm-datasource.rule=Host(`sub1.example.com`)"
      - "traefik.http.routers.tm-datasource.entrypoints=websecure"
      - "traefik.http.routers.tm-datasource.tls.certresolver=examplenetchallenge"
    networks:
      - default
      - project1
    volumes:
      - ./config.json:/etc/tesla-data-source/config.json:ro
      - ./custom_templates:/app/templates/custom:ro
```

Remember to change the tokens. 
Update the networks according to the other components (get inspired by **teslamate** service).
You can ignore the labels if not using Traefik.

### Environmental variables meaning
* TM_DB_USER: database user
* TM_DB_PASS: database password
* TM_DB_NAME: database name
* TM_DB_HOST: database host (server name)
* POST_CONFIG_TOKEN: token fro POST operations
* FIO_API_TOKEN: token for loading FIO account balance


### Volumes
* override default config.json
* map directory for custom templates

## Config file
If in doubt about the doc being up to date, take the sample config from source code.
The same structure is used to POST to update the config
```json
{
  "enabled": true,
  "carId": 1,
  "startLatitude": 49.321039,
  "startLongitude": 13.704535,
  "startRadius": 100,
  "startTime": "2020-12-28T10:30:00.000Z",
  "hours": 24,
  "mergeFromLap": 1,
  "lapsMerged": 1,
  "consumptionRated": 14.7,
  "statusRefreshSeconds": 5,
  "lapsRefreshSeconds": 10,
  "fioRefreshSeconds": 900,
  "defaultMapZoom": 16,
  "previousLaps": 10,
  "minTimeLap": 10,
  "mapLabels": [
    {
      "field": "car_name",
      "label": "Car",
      "default": "---"
    },
    {
      "field": "driver_name",
      "label": "Driver",
      "default": "---"
    }
  ],
  "textLabels": [
    {
      "field": "car_name",
      "label": "Car",
      "default": "---"
    },
    {
      "field": "start_time",
      "label": "Start time",
      "format_function": "format_datetime_fn",
      "format": "DD.MM.YYYY HH:mm:ss",
      "unit": "",
      "default": "---"
    },
    {
      "field": "end_time",
      "label": "End time",
      "format_function": "format_datetime_fn",
      "format": "DD.MM.YYYY HH:mm:ss",
      "unit": "",
      "default": "---"
    },
    {
      "field": "distance",
      "label": "Distance",
      "format_function": "format_float_fn",
      "format": "%.2f",
      "unit": "km",
      "default": "---"
    },
    {
      "field": "time_since_start",
      "label": "Time since start",
      "format_function": "format_period_words_fn",
      "unit": "",
      "default": "---"
    },
    {
      "field": "time_since_start",
      "label": "Time since start",
      "format_function": "format_period_fn",
      "unit": "",
      "default": "---"
    },
    {
      "field": "time_to_end",
      "label": "Time to end",
      "format_function": "format_period_fn",
      "unit": "",
      "default": "---"
    }
  ]
}
```

### Config fields meaning
* enabled: publishing the data is enabled [true]
* carId: car identifier from the database [1]
* startLatitude: latitude of starting point [49.321039]
* startLongitude: longitude of stating point [13.704535]
* startRadius: radius in meters from starting point used to initiate new lap [100]
* startTime: time to load and process data from ["2020-12-28T10:30:00.000Z"]
* hours: hours to be preocessed from startTime if provided, till now otherwise [24]
* mergeFromLap: the first lap to be merged [1]
* lapsMerged: how many laps are merged together [1]
* consumptionRated: rated consumption of the vehicle [14.7],
* statusRefreshSeconds: how often status data are refreshed from database [5]
* lapsRefreshSeconds: how often lap data are refreshed from database [10]
* fioRefreshSeconds: how often bank account balance is refreshed from bank API [900]
* defaultMapZoom: zoom level at page load. The higher, the closer (max 19) [16]
* previousLaps: number of previous laps to be displayed [10]
* minTimeLap: minimum number of seconds in pit or on lap to count it [10]
* mapLabels: labels displayed in the bubble on map
* textLabels: labels displayed next to the map

## Label formatting
```json
{
  "field": "distance",
  "label": "Distance",
  "format_function": "format_float_fn",
  "format": "%.2f",
  "unit": "km",
  "default": "---"
}
```
* field: any field available in CarStatus class
* label: displayed label
* format_function: formatting functions from labels.py (if not provided, output is just str())
* format: format string (used by the function) if needed
* unit: unit concatenated after the value
* default: default value used if the actual value is null/None

## JSON Endpoints

### GET /car_status_json
Get the car status. Remember some fields may be null based on the car status.
```json
{
    "date": "2020-12-28T22:29:21.939000",
    "latitude": 40.1234,
    "longitude": 10.123456,
    "speed": null,
    "power": 0.0,
    "odometer": 12345.6789,
    "ideal_battery_range_km": 286.38,
    "battery_level": 81,
    "outside_temp": null,
    "elevation": 455.0,
    "inside_temp": null,
    "est_battery_range_km": 186.06,
    "rated_battery_range_km": 358.45,
    "usable_battery_level": 80
}
```

### GET /fio_balance_json
Get FIO account balance. Only if token is provided.
The token is configured via env variable (see above).
```json
{
    "amount": 123.45,
    "currency": "CZK"
}
```

### GET /configuration
Gets the current configuration. See above for example

### POST /configuration?_token=???
Updates the current configuration. See above for example, how the payload looks like.
The token is configured via env variable (see above).

### POST /driver_change?_token=???
Insert new driver change. It invalidates the existing one. 
You can optionally specify the time but keep in mind it doesn't alter history (date_to) of existing records
The token is configured via env variable (see above).

```json
{
    "name": "John Doe"
}
```

```json
{
    "name": "John Doe",
    "dateFrom": "2020-12-28T11:32:17"
}
```

## Web endpoints

### GET /car_map
Gets the simple page with an OSM map displaying the current position and some data.

### GET /laps_table
Gets table of laps according to configured params. This one may get changed or disappear completely.

### GET /custom?_template=xxxx
Open page using custom templates (provided thru mapped volume). if the page in custom_templates folder (see mapping above) is a.html, use
```/custom?_template=custom/a.html```
