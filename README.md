# tesla-data-source
Present data from Tesla API scrapers like Teslamate or Tesla Logger (TODO) to web. Lap analyzer...

## Instalation
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
```

Remember to change the tokens. 
Update the networks according to the other components (get inspired by **teslamate** service).
You can ignore the labels if not using Traefik.

### Environmental variables meaning
* TM_DB_USER=${TM_DB_USER}
* TM_DB_PASS=${TM_DB_PASS}
* TM_DB_NAME=${TM_DB_NAME}
* TM_DB_HOST=database
* POST_CONFIG_TOKEN="abcdefgh"
* FIO_API_TOKEN="abcdefgh"

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
  "defaultMapZoom": 16
}
```

### Config fields meaning
* enabled: publishing the data is enabled [true]
* carId: car identifier from the database [1]
* startLatitude: latitude of starting point [49.321039]
* startLongitude: longitude of stating point [13.704535]
* startRadius: radius in meters from starting point used to initiate new lap [100]
* startTime: time to load and process data from ["2020-12-28T10:30:00.000Z"]
* hours: if startTime not provided, last xy hours are processed [24]
* mergeFromLap: the first lap to be merged [1]
* lapsMerged: how many laps are merged together [1]
* consumptionRated: rated consumption of the vehicle [14.7],
* statusRefreshSeconds: how often status data are refreshed from database [5]
* lapsRefreshSeconds: how often lap data are refreshed from database [10]
* fioRefreshSeconds: how often bank account balance is refreshed from bank API [900]
* defaultMapZoom: zoom level at page load. The higher, the closer (max 19) [16] 

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

## Web endpoints

### GET /car_map
Gets the simple page with an OSM map displaying the current position and some data.

### GET /laps_table
Gets table of laps according to configured params. This one may get changed or disappear completely.