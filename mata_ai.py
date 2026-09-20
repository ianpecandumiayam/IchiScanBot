import cv2
import numpy as np

def urutkan_titik(titik):
    titik = titik.reshape((4, 2))
    titik_baru = np.zeros((4, 2), dtype="float32")
    jumlah = titik.sum(axis=1)
    titik_baru[0] = titik[np.argmin(jumlah)]
    titik_baru[2] = titik[np.argmax(jumlah)]
    selisih = np.diff(titik, axis=1)
    titik_baru[1] = titik[np.argmin(selisih)]
    titik_baru[3] = titik[np.argmax(selisih)]
    return titik_baru

def cari_kertas(nama_file):
    print(f"\n========== TES FILE: {nama_file} ==========")
    img_original = cv2.imread(nama_file)
    
    if img_original is None:
        print(f"❌ Gambar {nama_file} ga ketemu cuy!")
        return

    tinggi_baru = 1000
    rasio = tinggi_baru / img_original.shape[0]
    lebar_baru = int(img_original.shape[1] * rasio)
    img = cv2.resize(img_original, (lebar_baru, tinggi_baru))
    
    hasil = img.copy()
    tinggi, lebar = img.shape[:2]
    luas_gambar = tinggi * lebar

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Sensitivitas Canny diturunin dikit biar ga nangkap serat terlalu banyak
    edges = cv2.Canny(blur, 30, 120)
    kernel = np.ones((5, 5), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"Jumlah total kontur ditemukan: {len(contours)}")

    kandidat = []

   # ==========================================
    # 3. GRAYSCALE & BLUR (Jalan Tengah)
    # ==========================================
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Balik pake Gaussian Blur, tapi ukurannya di-set (7, 7)
    # Ini cukup buat nge-blur serat kayu dan anyaman tiker, tapi pinggiran kertas aman
    blur = cv2.GaussianBlur(gray, (7, 7), 0)

    # ==========================================
    # 4. EDGE DETECTION (Tambal Celah Halus)
    # ==========================================
    # Threshold di-set standar biar ga terlalu banyak nangkep noise
    edges = cv2.Canny(blur, 30, 150)

    # Pake MORPH_CLOSE dengan kernel 5x5.
    # Ini bakal nyambungin garis putus di binder, tapi nggak ngerusak sudut struk test7
    kernel = np.ones((5, 5), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    # ==========================================
    # 5. CARI SEMUA KONTUR (Tetap sama kodingannya)
    # ==========================================
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print("Jumlah kontur ditemukan:", len(contours))

    kandidat = []
    luas_gambar = tinggi * lebar

    # ==========================================
    # 6. MESIN SCORING (Versi Normal, Tanpa Karet Gelang)
    # ==========================================
    for i, c in enumerate(contours):
        luas = cv2.contourArea(c)

        if luas < luas_gambar * 0.05:
            continue

        keliling = cv2.arcLength(c, True)
        
        # Toleransi dibalikin ke angka stabil
        sudut = cv2.approxPolyDP(c, 0.04 * keliling, True)

        # Balikin syarat wajib convex (melengkung wajar)
        if len(sudut) == 4 and cv2.isContourConvex(sudut):
            rasio_luas = (luas / luas_gambar) * 100
            score = rasio_luas
            
            # Kalo nangkep seluruh frame (kayak bug tiker tadi), langsung penalti
            if rasio_luas < 10 or rasio_luas > 90:
                score -= 50

            print(f"🔍 [Kandidat {i}] 4 sudut | Luas: {int(luas):>6} | Rasio: {rasio_luas:>4.1f}% | SCORE: {score:.1f}")
            
            kandidat.append({
                'score': score,
                'sudut': sudut,
                'luas': luas
            })

    # Urutin dari skor tertinggi ke terendah
    kandidat.sort(key=lambda x: x['score'], reverse=True)
    kertas_ditemukan = False

    # Kalo ada kandidat dan skor tertingginya masuk akal (di atas 0)
    if kandidat and kandidat[0]['score'] > 0:
        terbaik = kandidat[0]
        sudut = terbaik['sudut']
        titik_terurut = urutkan_titik(sudut)
        (tl, tr, br, bl) = titik_terurut

        lebar_atas = np.linalg.norm(tr - tl)
        lebar_bawah = np.linalg.norm(br - bl)
        tinggi_kiri = np.linalg.norm(bl - tl)
        tinggi_kanan = np.linalg.norm(br - tr)

        max_lebar = int(max(lebar_atas, lebar_bawah))
        max_tinggi = int(max(tinggi_kiri, tinggi_kanan))

        if max_lebar >= 100 and max_tinggi >= 100:
            titik_tujuan = np.array([
                [0, 0],
                [max_lebar - 1, 0],
                [max_lebar - 1, max_tinggi - 1],
                [0, max_tinggi - 1]
            ], dtype="float32")

            matrix = cv2.getPerspectiveTransform(titik_terurut, titik_tujuan)
            kertas_dicrop = cv2.warpPerspective(img, matrix, (max_lebar, max_tinggi))

            cv2.drawContours(hasil, [sudut], -1, (0, 255, 0), 5)
            for titik in titik_terurut:
                x, y = titik.astype(int)
                cv2.circle(hasil, (x, y), 10, (0, 0, 255), -1)

            kertas_ditemukan = True

    cv2.imshow("Mata AI - Ketemu Kotak", hasil)
    
    if kertas_ditemukan:
        print("✅ Kertas TERBAIK berhasil dieksekusi!")
        cv2.imshow("BOOM! Hasil Crop Lurus", kertas_dicrop)
    else:
        print("❌ Kertas gagal ditemukan atau skor terlalu jelek.")
        cv2.imshow("Edges (X-Ray)", edges)

    cv2.waitKey(0)
    cv2.destroyAllWindows()

# --- EKSEKUSI TES ---
# Hapus tanda pagar (#) buat ngetes file lu satu-satu
cari_kertas("test1.jpg")
#cari_kertas("test2.jpg")
#cari_kertas("test3.jpg")
#cari_kertas("test4.jpg")
#cari_kertas("test5.jpg")
#cari_kertas("test6.jpg")
#cari_kertas("test7.jpg")