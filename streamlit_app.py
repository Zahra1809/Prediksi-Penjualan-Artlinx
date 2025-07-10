import streamlit as st
import pandas as pd
import joblib
import altair as alt
from datetime import datetime
from io import BytesIO

# Konfigurasi halaman
st.set_page_config(page_title="Artlinx Sales Dashboard", layout="centered")

st.title("\U0001F4E6 Artlinx Sales Prediction Dashboard")
st.markdown("""
Dashboard ini menampilkan prediksi penjualan produk lokal di Artlinx Store berdasarkan data historis 2024,
serta memungkinkan simulasi prediksi penjualan berdasarkan input pengguna.
""")

# --- Load files ---
df_agg = pd.read_excel("hasil_prediksi_agregat_bulanan.xlsx")
model = joblib.load("model_prediksi_qty_artlinx.joblib")
le_merk = joblib.load("encoder_merk.pkl")
le_metode = joblib.load("encoder_metode.pkl")
df_produk = pd.read_excel("penjualan_artlinx_full_2024.xlsx")
df_produk = df_produk.drop_duplicates(subset="Nama Produk")

# --- Chart: Prediksi Penjualan ---
st.subheader("\U0001F4CA Prediksi Penjualan per Bulan")
df_agg['Periode'] = df_agg['bulan'].astype(str) + '-' + df_agg['tahun'].astype(str)
df_agg = df_agg.sort_values(by=['tahun', 'bulan'])
df_agg.set_index('Periode', inplace=True)

chart_data = pd.DataFrame({
    "Periode": df_agg.index,
    "Qty Aktual": df_agg['Qty Aktual'],
    "Qty Prediksi": df_agg['Qty Prediksi']
}).reset_index(drop=True)

chart_data = chart_data.melt(id_vars=['Periode'], var_name='Jenis', value_name='Qty')

line = alt.Chart(chart_data).mark_line(point=True).encode(
    x=alt.X('Periode:N', title='Periode'),
    y=alt.Y('Qty:Q', title='Qty'),
    color=alt.Color('Jenis:N', scale=alt.Scale(domain=['Qty Aktual', 'Qty Prediksi'], range=['green', 'red']))
).properties(
    width=700,
    height=400,
    title="Qty Aktual vs Prediksi per Bulan"
)

st.altair_chart(line, use_container_width=True)

# --- Tabel Ringkasan ---
st.subheader("\U0001F4CB Ringkasan Data Prediksi per Bulan")
st.dataframe(df_agg[['Qty Aktual', 'Qty Prediksi']], use_container_width=True)

# --- Simulasi Prediksi ---
st.subheader("\U0001F52E Simulasi Prediksi Penjualan")
tab1, tab2 = st.tabs(["\U0001F4DD Berdasarkan Merk (Utama)", "\U0001F4C1 Berdasarkan Nama Produk (Pelengkap)"])

# --- Tab 1: Berdasarkan Merk ---
with tab1:
    st.markdown("### Prediksi Penjualan Berdasarkan Merk")

    all_merks = sorted(df_produk[df_produk['Jenis Brand'] == 'LOKAL']['Merk'].unique())
    merk_input = st.selectbox("Pilih Merk", options=all_merks)
    bulan_input = st.selectbox("Bulan", options=list(range(1, 13)), index=6)
    tahun_input = st.selectbox("Tahun", options=[2024, 2025], index=1)
    diskon_default = st.slider("Diskon Default (%)", 0, 100, 10)

    if st.button("Prediksi Penjualan", key="predict_by_merk"):
        produk_merk = df_produk[(df_produk['Merk'] == merk_input) & (df_produk['Jenis Brand'] == 'LOKAL')].copy()
        if produk_merk.empty:
            st.warning("Tidak ada produk lokal dengan merk tersebut.")
        else:
            produk_merk['dayofweek'] = 0
            produk_merk['is_weekend'] = 0
            produk_merk['bulan'] = bulan_input
            produk_merk['tahun'] = tahun_input
            produk_merk['Metode Penjualan'] = 'Offline'
            produk_merk['Diskon'] = diskon_default

            produk_merk['Merk'] = le_merk.transform(produk_merk['Merk'])
            produk_merk['Metode Penjualan'] = le_metode.transform(produk_merk['Metode Penjualan'])

            df_model_input = produk_merk[['dayofweek', 'is_weekend', 'bulan', 'tahun',
                                           'Merk', 'Kategori ID', 'Metode Penjualan',
                                           'Harga Jual', 'Diskon']].copy()

            pred_qty = model.predict(df_model_input)
            produk_merk['Qty Diprediksi'] = pred_qty.round(2)

            hasil = produk_merk[['Nama Produk', 'Harga Jual', 'Kategori 1', 'Qty Diprediksi']].sort_values(by='Qty Diprediksi', ascending=False)
            st.markdown(f"### Hasil Prediksi - Merk: `{merk_input}` ({bulan_input}/{tahun_input})")
            st.dataframe(hasil, use_container_width=True)

            with st.expander("⬇️ Download Hasil"):
                output = BytesIO()
                hasil.to_excel(output, index=False, engine='openpyxl')
                st.download_button(
                    label="Download Excel",
                    data=output.getvalue(),
                    file_name=f"prediksi_{merk_input}_{bulan_input}_{tahun_input}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# --- Tab 2: Berdasarkan Nama Produk ---
with tab2:
    st.markdown("### Prediksi Penjualan Berdasarkan Nama Produk")

    col1, col2 = st.columns([2, 1])
    with col1:
        df_produk = df_produk[df_produk['Jenis Brand'] == 'LOKAL']
        nama_produk = st.selectbox("Nama Produk", options=sorted(df_produk['Nama Produk'].unique()))
        metode_penjualan = st.selectbox("Metode Penjualan", options=['Online', 'Offline'])
    with col2:
        produk_terpilih = df_produk[df_produk['Nama Produk'] == nama_produk].iloc[0]
        harga_jual = produk_terpilih['Harga Jual']
        diskon = st.slider("Diskon (%)", 0, 100, 10)
        tanggal = st.date_input("Tanggal Penjualan", value=datetime(2025, 7, 1))

    merk = produk_terpilih['Merk']
    kategori1 = produk_terpilih['Kategori 1']
    kategori2 = produk_terpilih['Kategori 2']
    kategori_id = produk_terpilih['Kategori ID']

    if merk not in le_merk.classes_:
        st.error(f"Merk '{merk}' tidak dikenal oleh model. Silakan pilih produk lain.")
    else:
        dayofweek = tanggal.weekday()
        is_weekend = 1 if dayofweek in [5, 6] else 0
        bulan = tanggal.month
        tahun = tanggal.year

        merk_encoded = le_merk.transform([merk])[0]
        metode_encoded = le_metode.transform([metode_penjualan])[0]

        data_uji = pd.DataFrame({
            'dayofweek': [dayofweek],
            'is_weekend': [is_weekend],
            'bulan': [bulan],
            'tahun': [tahun],
            'Merk': [merk_encoded],
            'Kategori ID': [kategori_id],
            'Metode Penjualan': [metode_encoded],
            'Harga Jual': [harga_jual],
            'Diskon': [diskon]
        })

        qty_prediksi = model.predict(data_uji)[0]

        st.markdown("### Hasil Prediksi")
        st.write(f"**Nama Produk:** {nama_produk}")
        st.write(f"**Merk:** {merk}")
        st.write(f"**Harga Jual:** Rp{harga_jual:,.0f}")
        st.write(f"**Metode Penjualan:** {metode_penjualan}")
        st.text(f"Kategori: {kategori1} / {kategori2}")
        st.text(f"Kategori ID: {kategori_id}")
        st.write(f"**Tanggal:** {tanggal.strftime('%d-%m-%Y')}")
        st.write(f"**Qty yang diprediksi:** {qty_prediksi:.2f} unit")
