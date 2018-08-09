fileName = input("Input file name : ")  # fat32.dd, fat32_2.dd
f = open(fileName, "rb")

boot_record = f.read(48)

bytesPerSector = int.from_bytes(boot_record[11:13], byteorder='little')         # 11 - 12
sectorPerCluster = int.from_bytes(boot_record[13:14], byteorder='little')       # 13
reservedSectorCount = int.from_bytes(boot_record[14:16], byteorder='little')    # 14 - 15
numberOfFats = int.from_bytes(boot_record[16:17], byteorder='little')           # 16
fatSize32 = int.from_bytes(boot_record[36:40], byteorder='little')              # 36 - 39
rootDirCluster = int.from_bytes(boot_record[44:48], byteorder='little')         # 44 - 47

bytes_per_cluster = bytesPerSector * sectorPerCluster

f.seek(reservedSectorCount * 512)  # fat1의 위치로 이동
fat1 = f.read(fatSize32*bytesPerSector)  # fat1의 전체 영역 할당

level = 0  # 디렉토리 또는 파일의 계층


def lfn_name(root_dir, i):
    name_part = ""
    name_part = name_part + root_dir[1+i:11+i].decode("UTF-16-LE")
    name_part = name_part + root_dir[14+i:26+i].decode("UTF-16-LE")
    name_part = name_part + root_dir[28+i:32+i].decode("UTF-16-LE")
    name = name_part
    return name


def print_dir(search_cluster, level):
    while True:
        # 탐색할 클러스터 위치로 이동
        f.seek((reservedSectorCount * bytesPerSector) + (fatSize32 * bytesPerSector * numberOfFats) +
               ((search_cluster - 2) * bytes_per_cluster))

        read_cluster = f.read(bytes_per_cluster)  # 1 클러스터 읽기

        i = 0  # Name[0]
        j = 11  # Attribute

        while read_cluster[i] != 0x00:
            name = ""
            ext = ""
            kind = ""
            is_deleted = "[exist]  "
            size = 0

            if read_cluster[j] == 0x0F:  # LFN 일 때
                while read_cluster[j] == 0x0F:  # Attribute가 0x0F가 아닐 때 까지
                    name = lfn_name(read_cluster, i) + name
                    i = i + 32
                    j = j + 32
                while b'\xef\xbf\xbf' == name[-1].encode() or b'\x00' == name[-1].encode():  # 파일, 디렉토리 명 빈 칸 제거
                    name = name[0:-1]
                size = int.from_bytes(read_cluster[28 + i:32 + i], byteorder='little')
                if read_cluster[j] & 0x10 == 0x10:  # 디렉토리 일 때
                    kind = "<DIRECTORY>"
                    if read_cluster[i] == 0xE5:  # 삭제된 디렉토리 일 때
                        is_deleted = "[deleted]"
                        print("|____" * level, kind, is_deleted, "[" + name + "]", "[%d bytes]" % size)
                    else:  # 존재하는 디렉토리 일 때
                        first_cluster_high = int.from_bytes(read_cluster[20 + i:22 + i], byteorder='little') << 16
                        first_cluster_low = int.from_bytes(read_cluster[26 + i:28 + i], byteorder='little')
                        first_cluster = first_cluster_high | first_cluster_low
                        print("|____" * level, kind, is_deleted, "[" + name + "]", "[%d bytes]" % size)
                        print_dir(first_cluster, level + 1)
                    i = i + 32
                    j = j + 32
                else:  # 파일 일 때
                    kind = "<FILE>     "
                    if read_cluster[i] == 0xE5:  # 삭제된 파일 일 때
                        is_deleted = "[deleted]"
                    i = i + 32
                    j = j + 32

            elif read_cluster[j] & 0x10 == 0x10:  # LFN이 아니면서 디렉토리 일 때
                kind = "<DIRECTORY>"
                ext = read_cluster[8 + i:11 + i].decode("EUC-KR")
                x = 3
                while b' ' == ext[-1].encode():  # 확장자 빈 칸 제거
                    ext = ext[0:-1]
                    x = x - 1
                    if x == 0:
                        break
                size = int.from_bytes(read_cluster[28 + i:32 + i], byteorder='little')
                if read_cluster[i] == 0xE5:  # 삭제된 디렉토리 일 때
                    is_deleted = "[deleted]"
                    name = read_cluster[1 + i:8 + i].decode("EUC-KR")
                    while b' ' == name[-1].encode():  # 디렉토리 명 빈 칸 제거
                        name = name[0:-1]
                    if ext == "":
                        print("|____" * level, kind, is_deleted, "[" + name + "]", "[%d bytes]" % size)
                    else:
                        print("|____" * level, kind, is_deleted, "[" + name + "." + ext + "]", "[%d bytes]" % size)
                elif read_cluster[i:8 + i] == b'.       ' or \
                        read_cluster[i:i + 8] == b'..      ':  # . 현재 디렉토리 .. 이전 디렉토리 일 때
                    name = read_cluster[i:i + 8].decode("EUC-KR")
                    while b' ' == name[-1].encode():  # 디렉토리 명 빈 칸 제거
                        name = name[0:-1]
                    print("|____" * level, kind, is_deleted, "[" + name + "]", "[%d bytes]" % size)
                else:  # 존재하는 디렉토리 일 때
                    name = read_cluster[i:8 + i].decode("EUC-KR")
                    while b' ' == name[-1].encode():  # 디렉토리 명 빈 칸 제거
                        name = name[0:-1]
                    first_cluster_high = int.from_bytes(read_cluster[20 + i:22 + i], byteorder='little') << 16
                    first_cluster_low = int.from_bytes(read_cluster[26 + i:28 + i], byteorder='little')
                    first_cluster = first_cluster_high | first_cluster_low
                    if ext == "":
                        print("|____" * level, kind, is_deleted, "[" + name + "]", "[%d bytes]" % size)
                    else:
                        print("|____" * level, kind, is_deleted, "[" + name + "." + ext + "]", "[%d bytes]" % size)
                    print_dir(first_cluster, level + 1)
                i = i + 32
                j = j + 32

            elif read_cluster[j] & 0x10 != 0x10:  # LFN이 아니면서 파일 일 때
                kind = "<FILE>     "
                ext = read_cluster[8 + i:11 + i].decode("EUC-KR")
                x = 3
                while b' ' == ext[-1].encode():  # 확장자 빈 칸 제거
                    ext = ext[0:-1]
                    x = x - 1
                    if x == 0:
                        break
                size = int.from_bytes(read_cluster[28 + i:32 + i], byteorder='little')
                if read_cluster[i] == 0xE5:  # 삭제된 파일 일 때
                    is_deleted = "[deleted]"
                    name = read_cluster[1 + i:8 + i].decode("EUC-KR")
                else:  # 존재하는 파일 일 때
                    name = read_cluster[i:8 + i].decode("EUC-KR")
                while b' ' == name[-1].encode():  # 파일명 빈 칸 제거
                    name = name[0:-1]
                i = i + 32
                j = j + 32

            else:
                i = i + 32
                j = j + 32

            if read_cluster[j - 32] & 0x10 == 0x10:  # 디렉토리 일 경우 미리 정보를 출력했기 때문에 pass
                pass
            elif ext == "":
                print("|____" * level, kind, is_deleted, "[" + name + "]", "[%d bytes]" % size)
            else:
                print("|____" * level, kind, is_deleted, "[" + name + "." + ext + "]", "[%d bytes]" % size)

        # 해당 클러스터가 클러스터 체인의 마지막 클러스터인지 확인하기 위한 조건문
        cluster_chain = int.from_bytes(fat1[search_cluster * 4:(search_cluster + 1) * 4], byteorder='little')\
                        & 0x0fffffff
        if cluster_chain >= 0x0000002 and cluster_chain <= 0xFFFFFEF:  # cluster_chain은 자신에게 연결된 다음 클러스터의 번호
            search_cluster = cluster_chain
        else:  # 클러스터 체인의 마지막 클러스터 또는 비어있는 클러스터 또는 예약된 클러스터 또는 불량 클러스터
            break


print_dir(rootDirCluster, level)

f.close()
