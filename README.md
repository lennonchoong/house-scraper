# For creating sheet token.json run sheet.py

# When creating new token.json a sheets.json is required, sheets.json can be generated on Google Cloud Admin Console for generating new project

# Format for sheets.json
```
{
    "installed": {
        "client_id": "",
        "project_id": "",
        "auth_uri": "",
        "token_uri": "",
        "auth_provider_x509_cert_url": "",
        "client_secret": "",
        "redirect_uris": [""]
    }
}
```

# Format for config.json
```
{
    "GOOGLE_MAP_API_KEY": "",
    "BEDROOMS": 3,
    "BATHROOMS": 2,
    "OFFICE_LOCATIONS": [[51.51295375732327, -0.09059168081330772], [51.51575097987736, -0.1317215344827178]],
    "MAX_DIST_TO_OFFICES": 12.5,
    "MIN_PRICE": 250,
    "MAX_PRICE": 310,
    "SPREADSHEET_ID": ""
}
```