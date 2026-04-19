#include <Uefi.h>
#include <Library/UefiLib.h>
#include <Library/UefiBootServicesTableLib.h>

EFI_STATUS
EFIAPI
UefiMain (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  Print(L"AxionFW Base: AxionBusBase.efi loaded.\r\n");
  Print(L"Scaffold UEFI app (QEMU/OVMF).\r\n");
  Print(L"Next: inventory + policy + security manifest.\r\n");
  return EFI_SUCCESS;
}
