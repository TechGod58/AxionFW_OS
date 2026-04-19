# AXION Settings Router Host Spec v1

Purpose: central route map so all category hosts are reachable from one Settings navigation layer.

## Routes
- /home -> home_host
- /system -> system_host
- /bluetooth-devices -> devices_host
- /network-internet -> network_host
- /personalization -> personalization_host
- /apps -> apps_host
- /accounts -> accounts_host
- /time-language -> language_host
- /accessibility -> accessibility_host
- /privacy-security -> privacy_security_host
- /updates -> updates_host

## Done criteria
- Route resolver returns host module + action map
- Invalid route returns deterministic error code
- Route change emits corr-traced event
