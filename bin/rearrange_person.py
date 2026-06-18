# -*- coding: utf-8 -*-
import os
import glob
import csv

def rearrange_person(path, dir1, memberlog, dir2, outfile, list_dir, period, dmax, dmin):
    # �t�@�C���p�X�̍\�z
    csvf = os.path.join(path, dir2, f"{outfile}.csv")
    datecsv = os.path.join(path, list_dir, f"{period}date.csv")
    inc_header_path = os.path.join(path, list_dir, "inc_header_list.txt")
    
    # �ǂݍ��ރ��O�t�@�C���̃p�^�[�������p
    membertmp_pattern = os.path.join(path, dir1, f"*{memberlog}.csv")

    # �C���V�f���g�w�b�_�[�̓ǂݍ���
    # PowerShell��Default�G���R�[�f�B���O�i���{��Windows�j�ɍ��킹��cp932���g�p
    incidents = []
    if os.path.exists(inc_header_path):
        with open(inc_header_path, 'r', encoding='cp932') as f:
            incidents = [line.strip() for line in f if line.strip()]

    # �x�[�X�ƂȂ���t�E�x���f�[�^�̓ǂݍ��� ($memberDat �̏�����)
    member_dat = []
    headers = ["date", "holiday"]
    with open(datecsv, 'r', encoding='cp932') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # dmin�ȏ�Admax�����̊��ԂŃt�B���^�����O
            if dmin <= row['date'] < dmax:
                member_dat.append({
                    'date': row['date'],
                    'holiday': row['holiday']
                })

    s = 1  # �d���w�b�_�[�p�̘A��

    # �Ώۃ��O�t�@�C���̏������[�v
    for filepath in glob.glob(membertmp_pattern):
        filename = os.path.basename(filepath)
        print(filename)
        
        # 1. �擪2�s�i���C���w�b�_�[�ƃT�u�w�b�_�[�j�̓ǂݍ���
        with open(filepath, 'r', encoding='cp932') as f:
            line1 = f.readline().split(',')
            line2 = f.readline().split(',')
            
            # �󔒂��������A�󕶎��̗v�f��r�� (PowerShell�� `? { $_ }` �ɑ���)
            tmp_headers = [x.strip() for x in line1 if x.strip()]
            sub_headers = [x.strip() for x in line2 if x.strip()]
            
        j = 0
        # �w�b�_�[�̒u�������E�d������
        for i in range(len(tmp_headers)):
            if i <= 1:
                continue
            
            # �C���V�f���g���X�g�ƈ�v���邩�m�F
            if tmp_headers[i] in incidents:
                if j < len(sub_headers):
                    tmp_headers[i] = sub_headers[j]
                else:
                    tmp_headers[i] = "�s���C���V�f���g"
                j += 1
            
            # �����̃w�b�_�[���Əd�����Ă��邩�̊m�F
            if tmp_headers[i] in tmp_headers[:i]:
                tmp = tmp_headers[i]
                tmp_headers[i] = f"{tmp_headers[i]}{s}"
                print(f"�w�b�_�[�ɏd��������܂�: {tmp}")
                s += 1

        total_time = 0.0
        
        # 2. 3�s�ڈȍ~�̃f�[�^�{�̂̓ǂݍ���
        with open(filepath, 'r', encoding='cp932') as f:
            # �擪2�s���X�L�b�v
            next(f)
            next(f)
            
            reader = csv.reader(f)
            file_data = []
            for row in reader:
                row_dict = {}
                for i in range(len(tmp_headers)):
                    if i < len(row):
                        row_dict[tmp_headers[i]] = row[i]
                file_data.append(row_dict)

        # 3. �}�X�^�[�f�[�^(member_dat)�̗�g��
        for i in range(len(tmp_headers)):
            if i <= 1:
                continue
            prop = tmp_headers[i]
            # �V�����J������������ΑS�̂̃w�b�_�[���X�g�ɒǉ����A�}�X�^�[�f�[�^�ɂ��󍀖ڂ�ǉ�
            if prop not in headers:
                headers.append(prop)
                for row in member_dat:
                    row[prop] = None

        # 4. �f�[�^�l�̏W�v�E�}�[�W
        for st in file_data:
            st_date = st.get('date')
            
            # �Y��������t�̍s�� member_dat ����T��
            target_row = next((r for r in member_dat if r['date'] == st_date), None)
            
            if target_row is not None:
                for i in range(len(tmp_headers)):
                    if i <= 1:
                        continue
                    prop = tmp_headers[i]
                    val = st.get(prop)
                    
                    # �l�����݂���ꍇ�̂݃}�X�^�[���X�V���A���H���ɉ��Z
                    if val is not None and val != "":
                        target_row[prop] = val
                        try:
                            total_time += float(val)
                        except ValueError:
                            pass # ���l�ɕϊ��ł��Ȃ��l�͖���
        
        print(f"{filename} ���H��: {total_time}\n")

    # 5. ���ʂ�CSV�֏o��
    with open(csvf, 'w', encoding='cp932', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(member_dat)

# --- ���s���̎g�p�� ---
# ���ۂɎ��s����ꍇ�͈ȉ��̂悤�ɕϐ����w�肵�Ċ֐����Ăяo���܂��B
# rearrange_person(
#     path="C:\\logs",
#     dir1="member_logs",
#     memberlog="log_suffix",
#     dir2="output",
#     outfile="merged_result",
#     list_dir="lists",
#     period="2023_04",
#     dmax="20230501",
#     dmin="20230401"
# )
