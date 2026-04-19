function Get-AxionEnvValue {
  param(
    [Parameter(Mandatory = $true)][string]$Name
  )

  foreach($scope in @('Process','User','Machine')){
    $value = [Environment]::GetEnvironmentVariable($Name, $scope)
    if(-not [string]::IsNullOrWhiteSpace($value)){
      return [pscustomobject]@{
        value = $value
        scope = $scope
      }
    }
  }

  return $null
}

function Set-AxionProcessEnvValue {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Value
  )

  [Environment]::SetEnvironmentVariable($Name, $Value, 'Process')
  Set-Item -Path ("Env:{0}" -f $Name) -Value $Value
}

function Convert-AxionSecureStringToPlainText {
  param(
    [Parameter(Mandatory = $true)][Security.SecureString]$SecureValue
  )

  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
  try {
    return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  } finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
  }
}

function Get-AxionKeyVaultSecretValue {
  param(
    [Parameter(Mandatory = $true)][string]$VaultName,
    [Parameter(Mandatory = $true)][string]$SecretName
  )

  if(-not (Get-Command Get-AzureKeyVaultSecret -ErrorAction SilentlyContinue)){
    Import-Module Az.KeyVault -ErrorAction SilentlyContinue | Out-Null
  }
  $azCmd = Get-Command Get-AzureKeyVaultSecret -ErrorAction SilentlyContinue
  if($null -ne $azCmd){
    $secret = Get-AzureKeyVaultSecret -VaultName $VaultName -Name $SecretName -ErrorAction Stop
    if($secret.PSObject.Properties.Name -contains 'SecretValueText' -and -not [string]::IsNullOrWhiteSpace([string]$secret.SecretValueText)){
      return [string]$secret.SecretValueText
    }
    if($secret.PSObject.Properties.Name -contains 'SecretValue' -and $null -ne $secret.SecretValue){
      return Convert-AxionSecureStringToPlainText -SecureValue $secret.SecretValue
    }
  }

  if(-not (Get-Command Get-AzureRmKeyVaultSecret -ErrorAction SilentlyContinue)){
    Import-Module AzureRM.KeyVault -ErrorAction SilentlyContinue | Out-Null
  }
  $azureRmCmd = Get-Command Get-AzureRmKeyVaultSecret -ErrorAction SilentlyContinue
  if($null -ne $azureRmCmd){
    $secret = Get-AzureRmKeyVaultSecret -VaultName $VaultName -Name $SecretName -ErrorAction Stop
    if($secret.PSObject.Properties.Name -contains 'SecretValueText' -and -not [string]::IsNullOrWhiteSpace([string]$secret.SecretValueText)){
      return [string]$secret.SecretValueText
    }
    if($secret.PSObject.Properties.Name -contains 'SecretValue' -and $null -ne $secret.SecretValue){
      return Convert-AxionSecureStringToPlainText -SecureValue $secret.SecretValue
    }
  }

  throw "No Azure Key Vault command is available. Install/import Az.KeyVault or AzureRM.KeyVault and authenticate first."
}

function Initialize-AxionReleaseSigningEnv {
  param(
    [string]$KmsEnvName = 'AXION_KMS_RELEASE_SIGNING_KEY_01',
    [string]$HsmEnvName = 'AXION_HSM_RELEASE_SIGNING_KEY_02',
    [switch]$UseKeyVault,
    [switch]$PromptIfMissing,
    [string]$KeyVaultName = '',
    [string]$KmsSecretName = '',
    [string]$HsmSecretName = '',
    [string]$KmsKeyFile = '',
    [string]$HsmKeyFile = ''
  )

  if([string]::IsNullOrWhiteSpace($KeyVaultName)){
    $KeyVaultName = [Environment]::GetEnvironmentVariable('AXION_RELEASE_KEYVAULT_NAME', 'Process')
    if([string]::IsNullOrWhiteSpace($KeyVaultName)){
      $KeyVaultName = [Environment]::GetEnvironmentVariable('AXION_RELEASE_KEYVAULT_NAME', 'User')
    }
  }
  if([string]::IsNullOrWhiteSpace($KmsSecretName)){
    $KmsSecretName = [Environment]::GetEnvironmentVariable('AXION_KMS_RELEASE_SIGNING_KEY_01_SECRET_NAME', 'Process')
    if([string]::IsNullOrWhiteSpace($KmsSecretName)){
      $KmsSecretName = [Environment]::GetEnvironmentVariable('AXION_KMS_RELEASE_SIGNING_KEY_01_SECRET_NAME', 'User')
    }
  }
  if([string]::IsNullOrWhiteSpace($HsmSecretName)){
    $HsmSecretName = [Environment]::GetEnvironmentVariable('AXION_HSM_RELEASE_SIGNING_KEY_02_SECRET_NAME', 'Process')
    if([string]::IsNullOrWhiteSpace($HsmSecretName)){
      $HsmSecretName = [Environment]::GetEnvironmentVariable('AXION_HSM_RELEASE_SIGNING_KEY_02_SECRET_NAME', 'User')
    }
  }
  if([string]::IsNullOrWhiteSpace($KmsKeyFile)){
    $KmsKeyFile = [Environment]::GetEnvironmentVariable('AXION_KMS_RELEASE_SIGNING_KEY_01_FILE', 'Process')
    if([string]::IsNullOrWhiteSpace($KmsKeyFile)){
      $KmsKeyFile = [Environment]::GetEnvironmentVariable('AXION_KMS_RELEASE_SIGNING_KEY_01_FILE', 'User')
    }
  }
  if([string]::IsNullOrWhiteSpace($HsmKeyFile)){
    $HsmKeyFile = [Environment]::GetEnvironmentVariable('AXION_HSM_RELEASE_SIGNING_KEY_02_FILE', 'Process')
    if([string]::IsNullOrWhiteSpace($HsmKeyFile)){
      $HsmKeyFile = [Environment]::GetEnvironmentVariable('AXION_HSM_RELEASE_SIGNING_KEY_02_FILE', 'User')
    }
  }

  $targets = @(
    [pscustomobject]@{
      env_name = $KmsEnvName
      key_file = $KmsKeyFile
      secret_name = $KmsSecretName
      prompt_label = 'KMS release signing key 01'
    },
    [pscustomobject]@{
      env_name = $HsmEnvName
      key_file = $HsmKeyFile
      secret_name = $HsmSecretName
      prompt_label = 'HSM release signing key 02'
    }
  )

  $details = @()
  foreach($target in $targets){
    $resolved = [ordered]@{
      env_name = $target.env_name
      ok = $false
      source = 'missing'
      value_length = 0
      error = $null
    }

    try {
      $existing = Get-AxionEnvValue -Name $target.env_name
      if($null -ne $existing){
        Set-AxionProcessEnvValue -Name $target.env_name -Value $existing.value
        $resolved.ok = $true
        $resolved.source = "env_{0}" -f ($existing.scope.ToLowerInvariant())
        $resolved.value_length = $existing.value.Length
        $details += [pscustomobject]$resolved
        continue
      }

      if(-not [string]::IsNullOrWhiteSpace($target.key_file)){
        if(-not (Test-Path -LiteralPath $target.key_file)){
          throw ("Configured key file not found for {0}: {1}" -f $target.env_name, $target.key_file)
        }
        $fileValue = (Get-Content -Path $target.key_file -Raw).Trim()
        if([string]::IsNullOrWhiteSpace($fileValue)){
          throw ("Configured key file is empty for {0}: {1}" -f $target.env_name, $target.key_file)
        }
        Set-AxionProcessEnvValue -Name $target.env_name -Value $fileValue
        $resolved.ok = $true
        $resolved.source = 'key_file'
        $resolved.value_length = $fileValue.Length
        $details += [pscustomobject]$resolved
        continue
      }

      if($UseKeyVault -and -not [string]::IsNullOrWhiteSpace($KeyVaultName) -and -not [string]::IsNullOrWhiteSpace($target.secret_name)){
        $kvValue = Get-AxionKeyVaultSecretValue -VaultName $KeyVaultName -SecretName $target.secret_name
        if([string]::IsNullOrWhiteSpace($kvValue)){
          throw ("Key Vault secret is empty for {0} ({1}/{2})" -f $target.env_name, $KeyVaultName, $target.secret_name)
        }
        Set-AxionProcessEnvValue -Name $target.env_name -Value $kvValue
        $resolved.ok = $true
        $resolved.source = 'key_vault'
        $resolved.value_length = $kvValue.Length
        $details += [pscustomobject]$resolved
        continue
      }

      if($PromptIfMissing){
        $secureInput = Read-Host -Prompt ("Enter {0}" -f $target.prompt_label) -AsSecureString
        $promptValue = Convert-AxionSecureStringToPlainText -SecureValue $secureInput
        if([string]::IsNullOrWhiteSpace($promptValue)){
          throw ("Prompted value is empty for {0}" -f $target.env_name)
        }
        Set-AxionProcessEnvValue -Name $target.env_name -Value $promptValue
        $resolved.ok = $true
        $resolved.source = 'prompt'
        $resolved.value_length = $promptValue.Length
        $details += [pscustomobject]$resolved
        continue
      }
    } catch {
      $resolved.error = $_.Exception.Message
    }

    $details += [pscustomobject]$resolved
  }

  $missing = @($details | Where-Object { -not $_.ok } | ForEach-Object { $_.env_name })
  return [pscustomobject][ordered]@{
    ok = ($missing.Count -eq 0)
    key_vault_name = $KeyVaultName
    attempted_key_vault = [bool]$UseKeyVault
    attempted_prompt = [bool]$PromptIfMissing
    details = $details
    missing = $missing
  }
}
