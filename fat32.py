def lfn_name(root_dir, i, name):
    name_part = ""
    name_part = name_part + root_dir[1+i:11+i].decode("UTF-16-LE")
    name_part = name_part + root_dir[14+i:26+i].decode("UTF-16-LE")
    name_part = name_part + root_dir[28+i:32+i].decode("UTF-16-LE")
    name = name_part + name
    return name


def print_dir(search_cluster, level, total_size, file_name):
    f = open(file_name, "rb")

    boot_record = f.read(40)
    bytes_per_sector = int.from_bytes(boot_record[11:13], byteorder='little')       # 11 - 12
    sector_per_cluster = int.from_bytes(boot_record[13:14], byteorder='little')     # 13
    reserved_sector_count = int.from_bytes(boot_record[14:16], byteorder='little')  # 14 - 15
    number_of_fats = int.from_bytes(boot_record[16:17], byteorder='little')         # 16
    fat_size32 = int.from_bytes(boot_record[36:40], byteorder='little')             # 36 - 39

    bytes_per_cluster = bytes_per_sector * sector_per_cluster
    f.seek((reserved_sector_count * bytes_per_sector) + (fat_size32 * bytes_per_sector * number_of_fats) + ((search_cluster - 2) * bytes_per_cluster))  # Data Area

    read_cluster = f.read(bytes_per_cluster)

    i = 0   # Name[0]
    j = 11  # Attribute

    if level == 1:
        total_size = 0

    while read_cluster[i] != 0x00:
        name = ""
        ext = ""
        kind = ""
        is_deleted = "[exist]  "
        size = 0

        if read_cluster[j] == 0x0F:  # LFN 일 때
            while read_cluster[j] == 0x0F:  # Attribute가 0x0F가 아닐 때 까지
                name = lfn_name(read_cluster, i, name)
                i = i + 32
                j = j + 32

            # 파일, 디렉토리 명 빈 칸 제거
            while b'\xef\xbf\xbf' == name[-1].encode() or b'\x00' == name[-1].encode():
                name = name[0:-1]
            if read_cluster[j] & 0x10 == 0x10:  # 디렉토리 일 때
                kind = "<DIRECTORY>"
                if read_cluster[i] == 0xE5:  # 삭제된 디렉토리 일 때
                    is_deleted = "[deleted]"
                    size = int.from_bytes(read_cluster[28+i:32+i], byteorder='little')
                    print("|----" * level, kind, is_deleted, "[" + name + "]", "[%d bytes]" % size)
                else:  # 존재하는 디렉토리 일 때
                    first_cluster_high = int.from_bytes(read_cluster[20+i:22+i], byteorder='little') << 16
                    first_cluster_low = int.from_bytes(read_cluster[26+i:28+i], byteorder='little')
                    first_cluster = first_cluster_high | first_cluster_low
                    total_size = print_dir(first_cluster, level+1, total_size, file_name)
                    print("|----" * level, kind, is_deleted, "[" + name + "]", "[%d bytes]" % total_size)
                i = i + 32
                j = j + 32
            else:  # 파일 일 때
                kind = "<FILE>     "
                size = int.from_bytes(read_cluster[28+i:32+i], byteorder='little')
                if read_cluster[i] == 0xE5:  # 삭제된 파일 일 때
                    is_deleted = "[deleted]"
                i = i + 32
                j = j + 32

        elif read_cluster[j] & 0x10 == 0x10:  # LFN이 아니면서 디렉토리 일 때
            kind = "<DIRECTORY>"
            ext = read_cluster[8+i:11+i].decode("EUC-KR")
            if read_cluster[i] == 0xE5:  # 삭제된 디렉토리 일 때
                is_deleted = "[deleted]"
                name = read_cluster[1+i:8+i].decode("EUC-KR")
                size = int.from_bytes(read_cluster[28 + i:32 + i], byteorder='little')
                print("|----" * level, kind, is_deleted, "[" + name + "]", "[%d bytes]" % size)
                if ext == "   ":
                    print("|----" * level, kind, is_deleted, "[" + name + "]", "[%d bytes]" % size)
                else:
                    print("|----" * level, kind, is_deleted, "[" + name + "." + ext + "]", "[%d bytes]" % size)
            elif read_cluster[i:8+i] == b'.       ' or read_cluster[i:i+8] == b'..      ':  # . 현재 디렉토리 .. 이전 디렉토리 일 때
                name = read_cluster[i:i+8].decode("EUC-KR")
                # 디렉토리 명 빈 칸 제거
                while b' ' == name[-1].encode():
                    name = name[0:-1]
                print("|----" * level, kind, is_deleted, "[" + name + "]", "[%d bytes]" % total_size)
            else:  # 존재하는 디렉토리 일 때
                name = read_cluster[i:8+i].decode("EUC-KR")
                # 디렉토리 명 빈 칸 제거
                while b' ' == name[-1].encode():
                    name = name[0:-1]
                first_cluster_high = int.from_bytes(read_cluster[20+i:22+i], byteorder='little') << 16
                first_cluster_low = int.from_bytes(read_cluster[26+i:28+i], byteorder='little')
                first_cluster = first_cluster_high | first_cluster_low
                total_size = print_dir(first_cluster, level + 1, total_size, file_name)
                if ext == "   ":
                    print("|----" * level, kind, is_deleted, "[" + name + "]", "[%d bytes]" % total_size)
                else:
                    print("|----" * level, kind, is_deleted, "[" + name + "." + ext + "]", "[%d bytes]" % total_size)
            i = i + 32
            j = j + 32

        elif read_cluster[j] & 0x10 != 0x10:  # LFN이 아니면서 파일 일 때
            kind = "<FILE>     "
            size = int.from_bytes(read_cluster[28+i:32+i], byteorder='little')
            ext = read_cluster[8+i:11+i].decode("EUC-KR")
            if read_cluster[i] == 0xE5:  # 삭제된 파일 일 때
                is_deleted = "[deleted]"
                name = read_cluster[1+i:8+i].decode("EUC-KR")
            else:  # 존재하는 파일 일 때
                name = read_cluster[i:8+i].decode("EUC-KR")
            # 파일명 빈 칸 제거
            while b' ' == name[-1].encode():
                name = name[0:-1]
            i = i + 32
            j = j + 32

        else:
            i = i + 32
            j = j + 32

        if read_cluster[j-32] & 0x10 == 0x10:  # 디렉토리 일 경우 미리 정보를 출력했기 때문에 pass
            pass
        elif ext == "":
            print("|----"*level, kind, is_deleted, "[" + name + "]", "[%d bytes]" % size)
        else:
            print("|----"*level, kind, is_deleted, "[" + name + "." + ext + "]", "[%d bytes]" % size)

        total_size = total_size + size
        if read_cluster[i] == 0x00:
            return total_size


fileName = input("Input file name : ") # fat32.dd, fat32_2.dd
f = open(fileName, "rb")
bootRecord = f.read(512)
f.close()
rootDirCluster = int.from_bytes(bootRecord[44:48], byteorder='little')  # 44 - 47
level = 0
totalSize = 0
print_dir(rootDirCluster, level, totalSize, fileName)
