/* Halaman tujuan tautan di email: kirim kode ke server, lalu masuk otomatis bila berhasil */
(async function () {
  await PC.renderNav();
  const $ = id => document.getElementById(id);
  const kode = new URLSearchParams(location.search).get("kode");
  const gagal = pesan => {
    $("judul").innerHTML = "Verifikasi<br>gagal"; $("ket").textContent = "";
    $("isi").textContent = pesan; $("kartu").hidden = false;
  };
  if (!kode) return gagal("Tautan tidak lengkap. Buka tautan langsung dari email verifikasi.");
  try {
    await PC.post("/api/verifikasi", { kode });
    $("judul").innerHTML = "Email<br>terverifikasi"; $("ket").textContent = "Akunmu aktif. Mengarahkan ke beranda…";
    setTimeout(() => PC.go("/"), 1600);
  } catch (e) {
    gagal(e.message + ". Daftar ulang atau minta tautan baru dari halaman Masuk.");
  }
})();
