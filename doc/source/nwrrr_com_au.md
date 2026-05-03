# North West Resource Recovery and Recycling (NWRRR)

Support for schedules provided by [North West Resource Recovery and Recycling](https://www.nwrrr.com.au), covering eight councils in Northwest Tasmania:

- Burnie
- Central Coast
- Circular Head
- Devonport City
- Kentish
- Latrobe
- Waratah-Wynyard
- West Coast

## Configuration via configuration.yaml

```yaml
waste_collection_schedule:
  sources:
    - name: nwrrr_com_au
      args:
        address: ADDRESS
```

### Configuration Variables

**address**  
*(string) (required)*

## Example

```yaml
waste_collection_schedule:
  sources:
    - name: nwrrr_com_au
      args:
        address: 14 Stirling Street, Burnie
```

## How to get the source arguments

Visit the [NWRRR collection map](https://www.nwrrr.com.au/map) and search for your address. Use your full street address including suburb (e.g. "14 Stirling Street, Burnie").
