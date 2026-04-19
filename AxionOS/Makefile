CC = gcc
LD = ld
OBJCOPY = objcopy
QEMU = qemu-system-x86_64

FW_CODE ?= $(shell ls /usr/share/OVMF/OVMF_CODE*.fd /usr/share/ovmf/OVMF_CODE*.fd 2>/dev/null | head -n 1)
FW_VARS ?= $(shell ls /usr/share/OVMF/OVMF_VARS*.fd /usr/share/ovmf/OVMF_VARS*.fd 2>/dev/null | head -n 1)
FW_MONO ?=

CFLAGS_EFI = -O2 -g -fpic -fshort-wchar -mno-red-zone -m64 -Wall -Wextra \
             -I/usr/include -I/usr/include/efi -I/usr/include/efi/x86_64 \
             -DEFI_FUNCTION_WRAPPER

CFLAGS_KERNEL = -O2 -g -ffreestanding -fno-stack-protector -fPIE \
                -mno-red-zone -m64 -Wall -Wextra -nostdlib -fno-builtin \
                -Ikernel/include

EFI_LDS = /usr/lib/elf_x86_64_efi.lds
EFI_CRT = /usr/lib/crt0-efi-x86_64.o
ESP_START_SECTOR = 2048
ESP_OFFSET_BYTES = 1048576

all: check-tools build/boot/BOOTX64.EFI build/kernel/axion.elf build/disk.img

check-tools:
	@command -v objcopy >/dev/null || (echo "ERROR: objcopy not found"; exit 1)
	@command -v mcopy  >/dev/null || (echo "ERROR: mtools not found"; exit 1)
	@command -v mmd    >/dev/null || (echo "ERROR: mtools not found"; exit 1)
	@command -v mformat >/dev/null || (echo "ERROR: mformat not found"; exit 1)
	@command -v sgdisk >/dev/null || (echo "ERROR: sgdisk not found (gdisk package)"; exit 1)
	@command -v $(QEMU) >/dev/null || (echo "ERROR: $(QEMU) not found"; exit 1)

build/boot/loader.o: boot/loader/loader.c
	mkdir -p build/boot
	$(CC) $(CFLAGS_EFI) -c $< -o $@

build/boot/BOOTX64.so: build/boot/loader.o
	$(LD) -nostdlib -znocombreloc -T $(EFI_LDS) -shared -Bsymbolic \
		$(EFI_CRT) $< -o $@ -L/usr/lib -lefi -lgnuefi

build/boot/BOOTX64.EFI: build/boot/BOOTX64.so
	$(OBJCOPY) -j .text -j .sdata -j .data -j .dynamic -j .dynsym -j .rel -j .rela -j .reloc \
		--target=efi-app-x86_64 $< $@

build/kernel/axion.elf:
	mkdir -p build/kernel/arch/x86_64
	python3 tools/kernel/generate_smart_driver_handoff.py --out-path out/runtime/smart_driver_kernel_handoff.json
	python3 tools/kernel/generate_parallel_cubed_hardware_guard.py --out-path out/runtime/parallel_cubed_hardware_guard.json
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/console.c -o build/kernel/console.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/hooks.c   -o build/kernel/hooks.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/main.c    -o build/kernel/main.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/panic.c   -o build/kernel/panic.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/telemetry.c -o build/kernel/telemetry.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/subsys/memory.c -o build/kernel/subsys_memory.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/subsys/irq.c -o build/kernel/subsys_irq.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/subsys/time.c -o build/kernel/subsys_time.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/subsys/ipc.c -o build/kernel/subsys_ipc.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/subsys/bus.c -o build/kernel/subsys_bus.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/subsys/parallel_guard.c -o build/kernel/subsys_parallel_guard.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/subsys/driver.c -o build/kernel/subsys_driver.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/subsys/userland.c -o build/kernel/subsys_userland.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/subsys/lifecycle.c -o build/kernel/subsys_lifecycle.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/runtime/e_runtime.c -o build/kernel/runtime_e_runtime.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/runtime/qm.c -o build/kernel/runtime_qm.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/runtime/ig.c -o build/kernel/runtime_ig.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/runtime/ledger.c -o build/kernel/runtime_ledger.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/runtime/qecc.c -o build/kernel/runtime_qecc.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/subsys/scheduler.c -o build/kernel/subsys_scheduler.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/subsys/security.c -o build/kernel/subsys_security.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/subsys/syscall.c -o build/kernel/subsys_syscall.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/drivers/acpi_handoff.c -o build/kernel/acpi_handoff.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/drivers/q35_chipset.c -o build/kernel/q35_chipset.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/drivers/e1000_probe.c -o build/kernel/e1000_probe.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/drivers/boot_diagnostics.c -o build/kernel/boot_diagnostics.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/drivers/reference_bsp_q35.c -o build/kernel/reference_bsp_q35.o
	$(CC) $(CFLAGS_KERNEL) -c kernel/src/drivers/virtio_blk_modern.c -o build/kernel/virtio_blk_modern.o
	$(CC) -O2 -g -ffreestanding -mno-red-zone -m64 -c kernel/src/arch/x86_64/start.S -o build/kernel/arch/x86_64/start.o
	$(CC) -nostdlib -pie -Wl,--no-dynamic-linker -Wl,-e,_start -Wl,-z,max-page-size=0x1000 -o $@ \
		build/kernel/console.o \
		build/kernel/hooks.o \
		build/kernel/main.o \
		build/kernel/panic.o \
		build/kernel/telemetry.o \
		build/kernel/subsys_memory.o \
		build/kernel/subsys_irq.o \
		build/kernel/subsys_time.o \
		build/kernel/subsys_ipc.o \
		build/kernel/subsys_bus.o \
		build/kernel/subsys_parallel_guard.o \
		build/kernel/subsys_driver.o \
		build/kernel/subsys_userland.o \
		build/kernel/subsys_lifecycle.o \
		build/kernel/runtime_e_runtime.o \
		build/kernel/runtime_qm.o \
		build/kernel/runtime_ig.o \
		build/kernel/runtime_ledger.o \
		build/kernel/runtime_qecc.o \
		build/kernel/subsys_scheduler.o \
		build/kernel/subsys_security.o \
		build/kernel/subsys_syscall.o \
		build/kernel/acpi_handoff.o \
		build/kernel/q35_chipset.o \
		build/kernel/e1000_probe.o \
		build/kernel/boot_diagnostics.o \
		build/kernel/reference_bsp_q35.o \
		build/kernel/virtio_blk_modern.o \
		build/kernel/arch/x86_64/start.o

build/disk.img: build/boot/BOOTX64.EFI build/kernel/axion.elf
	dd if=/dev/zero of=build/disk.img bs=1M count=64 status=none
	# GPT + ESP (EF00)
	sgdisk -og build/disk.img >/dev/null
	sgdisk -n 1:$(ESP_START_SECTOR):0 -t 1:EF00 -c 1:AXION_ESP build/disk.img >/dev/null
	# Format ESP at partition offset and install UEFI fallback boot path
	mformat -i build/disk.img@@$(ESP_OFFSET_BYTES) -F -v AXIONESP ::
	mmd -i build/disk.img@@$(ESP_OFFSET_BYTES) ::/EFI >/dev/null 2>&1 || true
	mmd -i build/disk.img@@$(ESP_OFFSET_BYTES) ::/EFI/BOOT >/dev/null 2>&1 || true
	mmd -i build/disk.img@@$(ESP_OFFSET_BYTES) ::/kernel >/dev/null 2>&1 || true
	mcopy -i build/disk.img@@$(ESP_OFFSET_BYTES) build/boot/BOOTX64.EFI ::/EFI/BOOT/BOOTX64.EFI
	mcopy -i build/disk.img@@$(ESP_OFFSET_BYTES) build/kernel/axion.elf ::/kernel/axion.elf

run: build/disk.img
	@if [ -n "$(FW_MONO)" ]; then \
		$(QEMU) -machine q35 -m 1024 \
			-drive if=pflash,format=raw,readonly=on,file="$(FW_MONO)" \
			-drive if=virtio,format=raw,file=build/disk.img \
			-serial stdio -display none; \
	elif [ -n "$(FW_CODE)" ] && [ -n "$(FW_VARS)" ]; then \
		$(QEMU) -machine q35 -m 1024 \
			-drive if=pflash,format=raw,readonly=on,file="$(FW_CODE)" \
			-drive if=pflash,format=raw,file="$(FW_VARS)" \
			-drive if=virtio,format=raw,file=build/disk.img \
			-serial stdio -display none; \
	else \
		echo "ERROR: no firmware image configured. Set FW_CODE/FW_VARS or FW_MONO."; \
		exit 1; \
	fi

clean:
	rm -rf build
