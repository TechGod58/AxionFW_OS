#include <efi.h>
#include <efilib.h>
#include <efiprot.h>
#include <stdint.h>

typedef struct {
    uint64_t fb_base; uint32_t fb_width; uint32_t fb_height; uint32_t fb_pixels_per_scanline; uint32_t fb_bpp;
    uint64_t rsdp; uint64_t mmap; uint64_t mmap_size; uint64_t mmap_desc_size; uint32_t mmap_desc_ver; uint64_t caps0; uint64_t caps1;
} ax_bootinfo_t;

typedef struct { unsigned char e_ident[16]; uint16_t e_type,e_machine; uint32_t e_version; uint64_t e_entry,e_phoff,e_shoff; uint32_t e_flags; uint16_t e_ehsize,e_phentsize,e_phnum,e_shentsize,e_shnum,e_shstrndx; } Elf64_Ehdr;
typedef struct { uint32_t p_type,p_flags; uint64_t p_offset,p_vaddr,p_paddr,p_filesz,p_memsz,p_align; } Elf64_Phdr;
typedef struct { uint32_t sh_name,sh_type; uint64_t sh_flags,sh_addr,sh_offset,sh_size; uint32_t sh_link,sh_info; uint64_t sh_addralign,sh_entsize; } Elf64_Shdr;
typedef struct { uint64_t r_offset,r_info; int64_t r_addend; } Elf64_Rela;

#define PT_LOAD 1
#define SHT_RELA 4
#define R_X86_64_RELATIVE 8
#define ELF64_R_TYPE(i) ((uint32_t)(i))
#define AX_CAP0_PREBOOT_AUTH (1ull << 0)
#define AX_CAP0_REPAIR_MODE  (1ull << 1)
#define AX_CAP0_MEMTEST64    (1ull << 2)
#define AX_CAP0_DISKTEST     (1ull << 3)

static UINT64 align_up(UINT64 x, UINT64 a){ return (x + (a-1)) & ~(a-1); }
static inline void com1c(char c){ __asm__ volatile("outb %0, %1" : : "a"((UINT8)c), "Nd"((UINT16)0x3f8)); }
static void com1s(const char *s){ while(*s) com1c(*s++); }
static void com1hex(UINT64 v){ const char* h="0123456789ABCDEF"; for(int i=15;i>=0;i--) com1c(h[(v>>(i*4))&0xF]); }
static void mark(const char *id){ com1s(id); com1c('\n'); }
static EFI_STATUS fail_stage(const char *id, EFI_STATUS st){ com1s("FAIL "); com1s(id); com1s(" ST="); com1hex((UINT64)st); com1c('\n'); return st; }

static int file_exists(EFI_FILE *root, CHAR16 *path){
    EFI_FILE *fh = NULL;
    EFI_STATUS st = uefi_call_wrapper(root->Open,5,root,&fh,path,EFI_FILE_MODE_READ,0);
    if(EFI_ERROR(st) || !fh) return 0;
    uefi_call_wrapper(fh->Close,1,fh);
    return 1;
}

static EFI_STATUS open_root(EFI_HANDLE ImageHandle, EFI_FILE **Root){
    EFI_LOADED_IMAGE *li=NULL; EFI_SIMPLE_FILE_SYSTEM_PROTOCOL *fs=NULL; EFI_STATUS st;
    st=uefi_call_wrapper(BS->HandleProtocol,3,ImageHandle,&gEfiLoadedImageProtocolGuid,(void**)&li); if(EFI_ERROR(st)) return st;
    st=uefi_call_wrapper(BS->HandleProtocol,3,li->DeviceHandle,&gEfiSimpleFileSystemProtocolGuid,(void**)&fs); if(EFI_ERROR(st)) return st;
    return uefi_call_wrapper(fs->OpenVolume,2,fs,Root);
}

static void probe_blockio_full(void){
    EFI_STATUS st; EFI_HANDLE *handles=NULL; UINTN count=0;
    st=uefi_call_wrapper(BS->LocateHandleBuffer,5,ByProtocol,&gEfiBlockIoProtocolGuid,NULL,&count,&handles);
    if(EFI_ERROR(st) || count==0){ com1s("DISK_SECTOR0_READ_FAIL\n"); return; }
    for(UINTN i=0;i<count;i++){
        EFI_BLOCK_IO *bio=NULL;
        st=uefi_call_wrapper(BS->HandleProtocol,3,handles[i],&gEfiBlockIoProtocolGuid,(void**)&bio);
        if(EFI_ERROR(st) || !bio || !bio->Media || !bio->Media->MediaPresent) continue;
        UINTN bs=bio->Media->BlockSize; if(bs==0) continue;
        VOID *buf=NULL; st=uefi_call_wrapper(BS->AllocatePool,3,EfiLoaderData,bs,&buf); if(EFI_ERROR(st)) continue;
        st=uefi_call_wrapper(bio->ReadBlocks,5,bio,bio->Media->MediaId,0,bs,buf);
        if(!EFI_ERROR(st)){ com1s("DISK_SECTOR0_READ_OK\n"); return; }
    }
    com1s("DISK_SECTOR0_READ_FAIL\n");
}

static void probe_network_full(void){
    EFI_STATUS st; EFI_HANDLE *handles=NULL; UINTN count=0;
    st=uefi_call_wrapper(BS->LocateHandleBuffer,5,ByProtocol,&gEfiSimpleNetworkProtocolGuid,NULL,&count,&handles);
    if(EFI_ERROR(st) || count==0){ com1s("NET_FULL_FAIL\n"); return; }
    for(UINTN i=0;i<count;i++){
        EFI_SIMPLE_NETWORK *snp=NULL;
        st=uefi_call_wrapper(BS->HandleProtocol,3,handles[i],&gEfiSimpleNetworkProtocolGuid,(void**)&snp);
        if(EFI_ERROR(st) || !snp || !snp->Mode) continue;
        if(snp->Mode->State==EfiSimpleNetworkStopped) uefi_call_wrapper(snp->Start,1,snp);
        if(snp->Mode->State!=EfiSimpleNetworkInitialized) uefi_call_wrapper(snp->Initialize,3,snp,0,0);
        if(snp->Mode->CurrentAddress.Addr[0] || snp->Mode->CurrentAddress.Addr[1] || snp->Mode->CurrentAddress.Addr[2] || snp->Mode->CurrentAddress.Addr[3] || snp->Mode->CurrentAddress.Addr[4] || snp->Mode->CurrentAddress.Addr[5]){
            com1s("NET_MAC=");
            for(int b=0;b<6;b++){ UINT8 v=snp->Mode->CurrentAddress.Addr[b]; const char *h="0123456789ABCDEF"; com1c(h[(v>>4)&0xF]); com1c(h[v&0xF]); if(b<5) com1c(':'); }
            com1c('\n');
            com1s("NET_FULL_OK\n");
            return;
        }
    }
    com1s("NET_FULL_FAIL\n");
}

EFI_STATUS EFIAPI efi_main(EFI_HANDLE ImageHandle, EFI_SYSTEM_TABLE *SystemTable){
    InitializeLib(ImageHandle,SystemTable);
    mark("L0");

    VOID *rsdp=NULL;
    for(UINTN i=0;i<SystemTable->NumberOfTableEntries;i++){ EFI_CONFIGURATION_TABLE *T=&SystemTable->ConfigurationTable[i]; if(CompareGuid(&T->VendorGuid,&AcpiTableGuid)){ rsdp=T->VendorTable; break; } }

    EFI_FILE *root=NULL,*kf=NULL; EFI_STATUS st=open_root(ImageHandle,&root); if(EFI_ERROR(st)) return fail_stage("OPEN_ROOT",st);

    // pre-EBS capability probes (full-tier smoke markers)
    probe_blockio_full();
    probe_network_full();
    st=uefi_call_wrapper(root->Open,5,root,&kf,L"\\kernel\\axion.elf",EFI_FILE_MODE_READ,0); if(EFI_ERROR(st)) return fail_stage("OPEN_KERNEL",st);
    mark("L1");

    Elf64_Ehdr eh; UINTN sz=sizeof(eh);
    st=uefi_call_wrapper(kf->Read,3,kf,&sz,&eh); if(EFI_ERROR(st)||sz!=sizeof(eh)) return fail_stage("READ_EHDR", EFI_LOAD_ERROR);
    if(!(eh.e_ident[0]==0x7f&&eh.e_ident[1]=='E'&&eh.e_ident[2]=='L'&&eh.e_ident[3]=='F'&&eh.e_ident[4]==2&&eh.e_machine==62)) return fail_stage("ELF_INVALID", EFI_UNSUPPORTED);
    mark("L2");

    UINTN phSize=eh.e_phnum*sizeof(Elf64_Phdr); Elf64_Phdr *ph=NULL;
    st=uefi_call_wrapper(BS->AllocatePool,3,EfiLoaderData,phSize,(void**)&ph); if(EFI_ERROR(st)) return fail_stage("ALLOC_PHDR",st);
    uefi_call_wrapper(kf->SetPosition,2,kf,eh.e_phoff); sz=phSize; st=uefi_call_wrapper(kf->Read,3,kf,&sz,ph); if(EFI_ERROR(st)||sz!=phSize) return fail_stage("READ_PHDR", EFI_LOAD_ERROR);

    UINT64 min_v=(UINT64)-1, max_v=0;
    for(UINTN i=0;i<eh.e_phnum;i++) if(ph[i].p_type==PT_LOAD){ if(ph[i].p_vaddr<min_v) min_v=ph[i].p_vaddr; if(ph[i].p_vaddr+ph[i].p_memsz>max_v) max_v=ph[i].p_vaddr+ph[i].p_memsz; }
    if(min_v==(UINT64)-1) return fail_stage("NO_LOAD_SEG", EFI_LOAD_ERROR);
    mark("L3");

    UINT64 span=align_up(max_v-min_v,0x1000); EFI_PHYSICAL_ADDRESS base=0; UINTN pages=(UINTN)(span/0x1000);
    st=uefi_call_wrapper(BS->AllocatePages,4,AllocateAnyPages,EfiLoaderData,pages,&base); if(EFI_ERROR(st)) return fail_stage("ALLOC_SPAN",st);
    com1s("BASE="); com1hex(base); com1c('\n');
    mark("L4");

    for(UINT64 z=0; z<span; z++) ((UINT8*)(UINTN)base)[z]=0;
    for(UINTN i=0;i<eh.e_phnum;i++){
        if(ph[i].p_type!=PT_LOAD) continue;
        UINT64 dest=(UINT64)base + (ph[i].p_vaddr - min_v);
        if(ph[i].p_filesz>0){ uefi_call_wrapper(kf->SetPosition,2,kf,ph[i].p_offset); UINTN rsz=(UINTN)ph[i].p_filesz; st=uefi_call_wrapper(kf->Read,3,kf,&rsz,(void*)(UINTN)dest); if(EFI_ERROR(st)||rsz!=ph[i].p_filesz) return fail_stage("COPY_SEG", EFI_LOAD_ERROR); }
    }
    mark("L5");

    UINTN reloc_count=0;
    if(eh.e_shoff && eh.e_shentsize==sizeof(Elf64_Shdr) && eh.e_shnum>0){
        UINTN shSize=eh.e_shentsize*eh.e_shnum; Elf64_Shdr *sh=NULL;
        st=uefi_call_wrapper(BS->AllocatePool,3,EfiLoaderData,shSize,(void**)&sh); if(EFI_ERROR(st)) return fail_stage("ALLOC_SHDR",st);
        uefi_call_wrapper(kf->SetPosition,2,kf,eh.e_shoff); sz=shSize; st=uefi_call_wrapper(kf->Read,3,kf,&sz,sh); if(EFI_ERROR(st)||sz!=shSize) return fail_stage("READ_SHDR", EFI_LOAD_ERROR);
        UINT64 delta=(UINT64)base - min_v;
        for(UINTN si=0; si<eh.e_shnum; si++) if(sh[si].sh_type==SHT_RELA && sh[si].sh_entsize==sizeof(Elf64_Rela)){
            UINTN n=(UINTN)(sh[si].sh_size / sizeof(Elf64_Rela));
            Elf64_Rela *rela=NULL; st=uefi_call_wrapper(BS->AllocatePool,3,EfiLoaderData,sh[si].sh_size,(void**)&rela); if(EFI_ERROR(st)) return fail_stage("ALLOC_RELA",st);
            uefi_call_wrapper(kf->SetPosition,2,kf,sh[si].sh_offset); UINTN rsz=sh[si].sh_size; st=uefi_call_wrapper(kf->Read,3,kf,&rsz,rela); if(EFI_ERROR(st)||rsz!=sh[si].sh_size) return fail_stage("READ_RELA", EFI_LOAD_ERROR);
            for(UINTN ri=0; ri<n; ri++){
                UINT32 typ=ELF64_R_TYPE(rela[ri].r_info);
                if(typ==R_X86_64_RELATIVE){ UINT64 *patch=(UINT64*)(UINTN)((UINT64)base + (rela[ri].r_offset - min_v)); *patch = delta + (UINT64)rela[ri].r_addend; reloc_count++; }
                else return fail_stage("RELOC_UNSUPPORTED", EFI_UNSUPPORTED);
            }
        }
    }
    com1s("RELOCS="); com1hex(reloc_count); com1c('\n');
    mark("L6");

    ax_bootinfo_t *bi=NULL; st=uefi_call_wrapper(BS->AllocatePool,3,EfiLoaderData,sizeof(ax_bootinfo_t),(void**)&bi); if(EFI_ERROR(st)) return fail_stage("ALLOC_BOOTINFO",st);
    for(UINTN i=0;i<sizeof(ax_bootinfo_t);i++) ((UINT8*)bi)[i]=0;
    bi->rsdp=(uint64_t)(UINTN)rsdp;
    bi->caps0 |= AX_CAP0_PREBOOT_AUTH;
    if(file_exists(root, L"\\EFI\\BOOT\\AXION.REPAIR")){ bi->caps0 |= AX_CAP0_REPAIR_MODE; com1s("BOOTFLAG_REPAIR\n"); }
    if(file_exists(root, L"\\EFI\\BOOT\\AXION.MEMTEST")){ bi->caps0 |= AX_CAP0_MEMTEST64; com1s("BOOTFLAG_MEMTEST\n"); }
    if(file_exists(root, L"\\EFI\\BOOT\\AXION.DISKTEST")){ bi->caps0 |= AX_CAP0_DISKTEST; com1s("BOOTFLAG_DISKTEST\n"); }

    UINTN mmapSize=0,mapKey=0,descSize=0; UINT32 descVer=0;
    uefi_call_wrapper(BS->GetMemoryMap,5,&mmapSize,NULL,&mapKey,&descSize,&descVer);
    mmapSize += descSize*8;
    EFI_MEMORY_DESCRIPTOR *mmap=NULL; st=uefi_call_wrapper(BS->AllocatePool,3,EfiLoaderData,mmapSize,(void**)&mmap); if(EFI_ERROR(st)) return fail_stage("ALLOC_MMAP",st);
    while(1){ UINTN cur=mmapSize; st=uefi_call_wrapper(BS->GetMemoryMap,5,&cur,mmap,&mapKey,&descSize,&descVer); if(EFI_ERROR(st)) return fail_stage("GET_MMAP",st); bi->mmap=(uint64_t)(UINTN)mmap; bi->mmap_size=(uint64_t)cur; bi->mmap_desc_size=(uint64_t)descSize; bi->mmap_desc_ver=descVer; st=uefi_call_wrapper(BS->ExitBootServices,2,ImageHandle,mapKey); if(st==EFI_INVALID_PARAMETER) continue; if(EFI_ERROR(st)) return fail_stage("EXIT_BS",st); break; }
    mark("L7");

    UINT64 entry = (UINT64)base + (eh.e_entry - min_v);
    com1s("ENTRY="); com1hex(entry); com1c('\n');
    mark("L8");
    typedef void (*kernel_entry_t)(void*);
    ((kernel_entry_t)(UINTN)entry)((void*)bi);
    return EFI_SUCCESS;
}
