import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model
import math
import io # Thư viện để tạo file ảo trên bộ nhớ tạm (dùng cho việc Download)

# ==========================================
# GIAO DIỆN WEB (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Phần Mềm Xếp Lịch", page_icon="📅", layout="centered")

st.title("📅 HỆ THỐNG XẾP THỜI KHÓA BIỂU")
st.markdown("---")

# 1. Các ô nhập liệu (thay thế cho tk.Entry)
col1, col2 = st.columns(2)
with col1:
    si_so_toi_da = st.number_input("Giới hạn Sĩ số tối đa 1 lớp:", min_value=1, value=45)
with col2:
    so_ca_hoc_toi_da = st.number_input("Số lượng Ca học (Vị trí):", min_value=1, value=4)

st.markdown("---")

# 2. Chức năng Tải File (Upload)
st.subheader("Bước 1: Tải lên danh sách đăng ký")
file_upload = st.file_uploader("Chọn file Excel (.xlsx)", type=['xlsx'])

# ==========================================
# HÀM XỬ LÝ LÕI (BỘ NÃO)
# ==========================================
def xu_ly_xep_lich(file_data, si_so_max, ca_hoc_max):
    # Đọc dữ liệu từ file người dùng upload (thay vì đọc từ ổ cứng)
    du_lieu = pd.read_excel(file_data).fillna('')
    danh_sach_cot_mon = list(du_lieu.columns)[2:]
    
    danh_sach_dang_ky = {}
    thong_tin_hs = {}
    thong_ke_mon = {mon: 0 for mon in danh_sach_cot_mon}
    
    cau_hinh_so_lop = {}
    cau_hinh_max_lop_ca = {}

    for index, row in du_lieu.iterrows():
        ten_hs_raw = str(row.iloc[0]).strip()
        ten_kiem_tra = ten_hs_raw.upper()
        
        if ten_kiem_tra == 'CAUHINH_SOLOP':
            for mon in danh_sach_cot_mon:
                try:
                    val = str(row[mon]).strip()
                    if val != '': cau_hinh_so_lop[mon] = int(float(val)) 
                except: pass
            continue
            
        if ten_kiem_tra == 'CAUHINH_MAX_LOP_CA':
            for mon in danh_sach_cot_mon:
                try:
                    val = str(row[mon]).strip()
                    if val != '': cau_hinh_max_lop_ca[mon] = int(float(val)) 
                except: pass
            continue
        
        lop_goc = str(row.iloc[1]).strip()
        if not ten_hs_raw: continue 
        
        ma_hs = f"HS_{index}"
        cac_mon_hoc = []
        
        for mon in danh_sach_cot_mon:
            if str(row[mon]).strip().lower() == 'x':
                cac_mon_hoc.append(mon)
                thong_ke_mon[mon] += 1
        
        danh_sach_dang_ky[ma_hs] = cac_mon_hoc
        thong_tin_hs[ma_hs] = {'Ten': ten_hs_raw, 'Lop': lop_goc}

    danh_sach_lop_hoc = []
    mon_cua_lop = {} 
    
    for mon, so_luong in thong_ke_mon.items():
        if so_luong > 0:
            if mon in cau_hinh_so_lop and cau_hinh_so_lop[mon] > 0:
                so_lop_can_mo = cau_hinh_so_lop[mon]
            else:
                so_lop_can_mo = math.ceil(so_luong / si_so_max)
            
            for i in range(1, so_lop_can_mo + 1):
                ten_lop = f"{mon}_{i}"
                danh_sach_lop_hoc.append(ten_lop)
                mon_cua_lop[ten_lop] = mon

    model = cp_model.CpModel()
    
    xep_hs_vao_lop = {}
    for ma_hs in danh_sach_dang_ky.keys():
        for lop in danh_sach_lop_hoc:
            xep_hs_vao_lop[(ma_hs, lop)] = model.NewBoolVar(f'hs_{ma_hs}_lop_{lop}')
            
    xep_lop_vao_ca = {}
    for lop in danh_sach_lop_hoc:
        for ca in range(1, ca_hoc_max + 1):
            xep_lop_vao_ca[(lop, ca)] = model.NewBoolVar(f'lop_{lop}_ca_{ca}')

    for ma_hs, cac_mon in danh_sach_dang_ky.items():
        for mon in danh_sach_cot_mon:
            cac_lop_cua_mon_nay = [lop for lop in danh_sach_lop_hoc if mon_cua_lop[lop] == mon]
            if not cac_lop_cua_mon_nay: continue
            if mon in cac_mon:
                model.AddExactlyOne(xep_hs_vao_lop[(ma_hs, lop)] for lop in cac_lop_cua_mon_nay)
            else:
                for lop in cac_lop_cua_mon_nay: model.Add(xep_hs_vao_lop[(ma_hs, lop)] == 0)

    for lop in danh_sach_lop_hoc:
        model.Add(sum(xep_hs_vao_lop[(ma_hs, lop)] for ma_hs in danh_sach_dang_ky.keys()) <= si_so_max)

    for lop in danh_sach_lop_hoc:
        model.AddExactlyOne(xep_lop_vao_ca[(lop, ca)] for ca in range(1, ca_hoc_max + 1))

    for ma_hs in danh_sach_dang_ky.keys():
        for ca in range(1, ca_hoc_max + 1):
            cac_lop_hs_hoc_trong_ca_nay = []
            for lop in danh_sach_lop_hoc:
                b = model.NewBoolVar(f'b_{ma_hs}_{lop}_{ca}')
                model.AddMultiplicationEquality(b, [xep_hs_vao_lop[(ma_hs, lop)], xep_lop_vao_ca[(lop, ca)]])
                cac_lop_hs_hoc_trong_ca_nay.append(b)
            model.Add(sum(cac_lop_hs_hoc_trong_ca_nay) <= 1)
    
    for mon in danh_sach_cot_mon:
        cac_lop_cua_mon_nay = [lop for lop in danh_sach_lop_hoc if mon_cua_lop[lop] == mon]
        if not cac_lop_cua_mon_nay: continue
        gioi_han_max = cau_hinh_max_lop_ca.get(mon, len(cac_lop_cua_mon_nay))
        for ca in range(1, ca_hoc_max + 1):
            model.Add(sum(xep_lop_vao_ca[(lop, ca)] for lop in cac_lop_cua_mon_nay) <= gioi_han_max)

    diem_thuong = []
    lop_thuoc_ca_1_2 = {}
    for lop in danh_sach_lop_hoc:
        b = model.NewBoolVar(f'ca12_{lop}')
        if ca_hoc_max >= 2:
            model.Add(b == xep_lop_vao_ca[(lop, 1)] + xep_lop_vao_ca[(lop, 2)])
        elif ca_hoc_max == 1:
            model.Add(b == xep_lop_vao_ca[(lop, 1)])
        else:
            model.Add(b == 0)
        lop_thuoc_ca_1_2[lop] = b

    for mon in danh_sach_cot_mon:
        cac_lop_cua_mon = [lop for lop in danh_sach_lop_hoc if mon_cua_lop[lop] == mon]
        if not cac_lop_cua_mon: continue
        nhom_hs_theo_lop = {}
        for ma_hs, cac_mon_hs in danh_sach_dang_ky.items():
            if mon in cac_mon_hs:
                lg = thong_tin_hs[ma_hs]['Lop']
                if lg not in nhom_hs_theo_lop: nhom_hs_theo_lop[lg] = []
                nhom_hs_theo_lop[lg].append(ma_hs)
                
        for lg, ds_hs in nhom_hs_theo_lop.items():
            if len(ds_hs) < 2: continue
            for i in range(len(ds_hs)):
                for j in range(i+1, len(ds_hs)):
                    hs1 = ds_hs[i]
                    hs2 = ds_hs[j]
                    for lop in cac_lop_cua_mon:
                        thuong = model.NewBoolVar(f'thuong_{hs1}_{hs2}_{lop}')
                        model.AddMinEquality(thuong, [
                            xep_hs_vao_lop[(hs1, lop)], 
                            xep_hs_vao_lop[(hs2, lop)], 
                            lop_thuoc_ca_1_2[lop]
                        ])
                        diem_thuong.append(thuong)

    if diem_thuong:
        model.Maximize(sum(diem_thuong))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 300.0 
    ket_qua = solver.Solve(model)

    if ket_qua in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        du_lieu_lop = []
        for lop in danh_sach_lop_hoc:
            ca_cua_lop = next(ca for ca in range(1, ca_hoc_max + 1) if solver.Value(xep_lop_vao_ca[(lop, ca)]))
            si_so = sum(solver.Value(xep_hs_vao_lop[(ma_hs, lop)]) for ma_hs in danh_sach_dang_ky.keys())
            du_lieu_lop.append({'Tên Lớp': lop, 'Môn': mon_cua_lop[lop], 'Sĩ số': si_so, 'Vị trí Ca Học': f"Ca {ca_cua_lop}"})
        
        du_lieu_hs = []
        for ma_hs in danh_sach_dang_ky.keys():
            dong_hs = {
                'Tên Học Sinh': thong_tin_hs[ma_hs]['Ten'],
                'Lớp Hành Chính': thong_tin_hs[ma_hs]['Lop']
            }
            for ca in range(1, ca_hoc_max + 1): dong_hs[f'Ca {ca}'] = "" 
            
            for lop in danh_sach_lop_hoc:
                if solver.Value(xep_hs_vao_lop[(ma_hs, lop)]):
                    ca_cua_lop = next(ca for ca in range(1, ca_hoc_max + 1) if solver.Value(xep_lop_vao_ca[(lop, ca)]))
                    dong_hs[f'Ca {ca_cua_lop}'] = lop
            du_lieu_hs.append(dong_hs)

        df_lop = pd.DataFrame(du_lieu_lop).sort_values(by=['Vị trí Ca Học', 'Tên Lớp'])
        df_hs = pd.DataFrame(du_lieu_hs)
        
        # Tạo file ảo trên bộ nhớ thay vì lưu ổ cứng
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_lop.to_excel(writer, sheet_name='Danh Sách Lớp', index=False)
            df_hs.to_excel(writer, sheet_name='TKB Học Sinh', index=False)
            
        thong_diep = "Hoàn hảo" if ket_qua == cp_model.OPTIMAL else "Tốt nhất"
        return True, output.getvalue(), f"🎉 Xếp lịch thành công mức độ {thong_diep}!"
    else:
        return False, None, "❌ Thất bại! Số ca học quá ít hoặc cấu hình Excel quá khắt khe."

# ==========================================
# CHẠY VÀ HIỂN THỊ KẾT QUẢ
# ==========================================
if file_upload is not None:
    st.success("✅ Đã tải file thành công!")
    st.subheader("Bước 2: Chạy Thuật Toán")
    
    if st.button("▶ BẮT ĐẦU XẾP LỊCH", type="primary"):
        # Tính năng Progress Bar tích hợp sẵn của Streamlit
        with st.spinner('⏳ Hệ thống đang suy nghĩ (tối đa 60 giây)...'):
            thanh_cong, file_ket_qua, thong_diep = xu_ly_xep_lich(file_upload, si_so_toi_da, so_ca_hoc_toi_da)
            
        if thanh_cong:
            st.success(thong_diep)
            st.subheader("Bước 3: Tải Kết Quả")
            
            # Nút Download File thay thế cho việc ghi đè
            st.download_button(
                label="📥 TẢI FILE EXCEL THỜI KHÓA BIỂU",
                data=file_ket_qua,
                file_name="KetQua_XepLich.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error(thong_diep)
