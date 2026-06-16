# kamus AI
WASTE_DICTIONARY = {
    "botol_plastik": {
        "nama": "Botol Plastik (PET/HDPE)",
        "kategori": "Recyclable",  # <--- Bernilai ekonomi tinggi
        "action": "Kosongkan sisa cairan, bilas singkat, lepaskan label kemasan, lalu gepengkan botol untuk menghemat ruang sebelum dibuang ke wadah daur ulang.",
        "sumber_dataset": "Clear plastic bottle, Plastic bottle, Container for household chemicals",
        "konteks": "Sering digunakan untuk kemasan air mineral atau bahan kimia rumah tangga. Membutuhkan waktu hingga 450 tahun untuk terurai secara alami."
    },
    "kantong_kresek": {
        "nama": "Kantong Kresek",
        "kategori": "Low-Value / Hard to Recycle", # <--- Sering menyumbat mesin daur ulang
        "action": "Pastikan kering dan bersih dari sisa makanan. Lipat dengan rapi. Sebaiknya gunakan kembali (reuse) sebagai kantong sampah rumah tangga atau kumpulkan ke dropbox daur ulang khusus plastik kemasan fleksibel.",
        "sumber_dataset": "Single-use carrier bag, Plastic bag",
        "konteks": "Sangat ringan, mudah terbawa angin ke lautan, dan sering tertelan oleh hewan laut seperti penyu karena menyerupai ubur-ubur."
    },
    "bungkus_kemasan": {
        "nama": "Bungkus Kemasan / Sachet",
        "kategori": "Non-Recyclable", # <--- Multilayer film hampir tidak laku di pengepul
        "action": "Gunting kemasan, bersihkan sisa minyak atau makanan di dalamnya, keringkan. Karena sulit didaur ulang secara massal, sampah ini sangat direkomendasikan untuk diolah mandiri menjadi ecobrick.",
        "sumber_dataset": "Plastic film, Crisp packet, Food Packet, Stretch film",
        "konteks": "Biasanya terbuat dari plastik multilapis (multilayer) yang sangat sulit didaur ulang secara konvensional."
    },
    "gelas_plastik": {
        "nama": "Gelas Plastik",
        "kategori": "Recyclable", # <--- Biasanya berbahan PP atau PET yang laku dijual
        "action": "Buang sisa es batu atau minuman, lepas sedotan dan plastik segel pelindung (seal cup), lalu tumpuk gelas secara vertikal sebelum dibuang ke tempat sampah daur ulang.",
        "sumber_dataset": "Disposable plastic cup, Plastic cup",
        "konteks": "Sering digunakan pada industri minuman (kopi es, boba). Umumnya terbuat dari plastik PP (Polypropylene) atau PET."
    },
    "tutup_botol": {
        "nama": "Tutup Botol Plastik",
        "kategori": "Hazard / Environmental Threat", # <--- Berbahaya bagi satwa karena ukuran kecil
        "action": "Jangan dibuang terpisah dalam keadaan lepas. Pasang kembali dengan erat pada botol plastiknya yang sudah digepengkan agar tidak tercecer dan menyelinap keluar saat proses penyaringan sampah di TPA.",
        "sumber_dataset": "Plastic bottle cap, Plastic caps",
        "konteks": "Ukurannya yang kecil membuatnya sangat rentan lolos dari sistem penyaringan sampah dan menjadi mikroplastik yang mematikan bagi burung laut."
    },
    "sedotan_plastik": {
        "nama": "Sedotan Plastik",
        "kategori": "Hazard / Environmental Threat", # <--- Polutan laut paling masif
        "action": "Hindari memotong sedotan menjadi bagian kecil karena mempercepat terciptanya mikroplastik. Ikat menjadi satu kesatuan jika jumlahnya banyak, atau masukkan ke dalam botol plastik bekas sebagai material ecobrick.",
        "sumber_dataset": "Plastic straw",
        "konteks": "Sulit didaur ulang karena bentuk dan ukurannya. Termasuk dalam daftar 10 sampah terbanyak yang ditemukan di pesisir pantai global."
    },
    "styrofoam": {
        "nama": "Styrofoam",
        "kategori": "Hazard & Non-Recyclable", # <--- Mengandung zat karsinogenik dan rapuh
        "action": "Patahkan menjadi bagian yang ringkas jika ukurannya besar, pastikan tidak ada sisa makanan basah yang menempel. Masukkan ke dalam kantong sampah residu karena styrofoam tidak diterima oleh industri daur ulang biasa.",
        "sumber_dataset": "Styrofoam piece, Ramen Cup, Disposable tableware",
        "konteks": "Sangat rapuh, mudah pecah menjadi partikel kecil, dan dapat menyerap racun kimia di lautan. Hampir tidak mungkin didaur ulang dengan biaya murah."
    }
}