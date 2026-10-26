#include <stdio.h>
#include "ftd2xx.h"

int main(void){
    DWORD n=0; 
    if (FT_CreateDeviceInfoList(&n) != FT_OK) {
        fprintf(stderr, "FT_CreateDeviceInfoList failed\n");
        return 1;
    }
    printf("# devices=%lu\n", (unsigned long)n);
    for (DWORD i=0;i<n;i++){
        DWORD flags=0, type=0, id=0, locId=0; 
        char sn[64]={0}, desc[64]={0}; 
        FT_HANDLE h=0;
        if (FT_GetDeviceInfoDetail(i,&flags,&type,&id,&locId, sn, desc, &h)==FT_OK) {
            printf("index=%lu  serial=%s  desc=%s  flags=0x%lx  locId=%lu\n",
                   (unsigned long)i,sn,desc,(unsigned long)flags,(unsigned long)locId);
        }
    }
    return 0;
}
