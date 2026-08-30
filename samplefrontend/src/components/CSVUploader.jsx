export default function CSVUploader({ file, setFile }) {

  function handleFile(event) {
    const selectedFile = event.target.files[0];

    if (!selectedFile) return;

    if (!selectedFile.name.endsWith(".csv")) {
      alert("Please select a CSV file.");
      return;
    }

    setFile(selectedFile);
  }

  return (
    <div className="csv-uploader">

      <label className="upload-button">
        📁
        {file ? file.name : "Upload CSV"}

        <input
          type="file"
          accept=".csv"
          onChange={handleFile}
          hidden
        />
      </label>

      {file && (
        <span className="file-status">
          ✓ Ready
        </span>
      )}

    </div>
  );
}