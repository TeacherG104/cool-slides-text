<!DOCTYPE html>
<html>
  <head>
    <style>
      body { font-family: Arial, sans-serif; padding: 10px; }
      input, button, select { margin: 5px 0; }
      #previewImage { max-width: 100%; border: 1px solid #ccc; margin-top: 10px; }
      #status { margin-top: 10px; color: green; }
      #fontSizeLabel { margin-top: 10px; display: block; }
    </style>
  </head>
  <body>
    <input id="text" placeholder="Enter text">
    <br>
    <label>Text color: <input id="color" type="color" value="#000000"></label>
    <br>
    <label>Background color: <input id="bg" type="color" value="#ffffff"></label>
    <br>
    <label id="fontSizeLabel">Font size: 
      <input id="fontSize" type="range" min="12" max="72" value="24">
      <span id="fontSizeValue">24</span>px
    </label>
    <br>
    <label><input id="trimToggle" type="checkbox"> Trim background to text size</label>
    <br>

    <!-- Font dropdown -->
    <label>Font:
      <select id="fontSelect">
        <option value="sans">Sans</option>
        <option value="serif">Serif</option>
        <option value="handwriting">Handwriting</option>
        <option value="display">Display</option>
      </select>
    </label>
    <br>

    <!-- Gradient color pickers -->
    <label>Gradient start: <input id="gradStart" type="color" value="#ff0000"></label>
    <br>
    <label>Gradient end: <input id="gradEnd" type="color" value="#0000ff"></label>
    <br>

    <!-- Transparent background toggle -->
    <label><input id="transparentToggle" type="checkbox"> Transparent background</label>
    <br>

    <button id="insertBtn">Insert into Slide</button>

    <img id="previewImage">
    <div id="status"></div>

    <script>
      function buildUrl() {
        const text = document.getElementById('text').value;
        const color = document.getElementById('color').value;
        const bg = document.getElementById('bg').value;
        const fontSize = document.getElementById('fontSize').value;
        const trim = document.getElementById('trimToggle').checked ? "true" : "false";
        const font = document.getElementById('fontSelect').value;
        const gradStart = document.getElementById('gradStart').value;
        const gradEnd = document.getElementById('gradEnd').value;
        const transparent = document.getElementById('transparentToggle').checked ? "true" : "false";

        return "https://cool-slides-text.onrender.com/render?"
          + "text=" + encodeURIComponent(text)
          + "&color=" + encodeURIComponent(color)
          + "&bg_color=" + encodeURIComponent(bg)
          + "&font_size=" + encodeURIComponent(fontSize)
          + "&trim=" + trim
          + "&font=" + encodeURIComponent(font)
          + "&grad_start=" + encodeURIComponent(gradStart)
          + "&grad_end=" + encodeURIComponent(gradEnd)
          + "&transparent=" + transparent;
      }

      function updatePreview() {
        const url = buildUrl();
        document.getElementById('previewImage').src = url;
        window.latestImageUrl = url;
        document.getElementById('status').textContent = "Preview updated.";
      }

      function insertIntoSlide() {
        if (!window.latestImageUrl) {
          alert("Generate a preview first!");
          return;
        }
        document.getElementById('status').textContent = "Inserting into slide...";
        google.script.run
          .withSuccessHandler(() => {
            document.getElementById('status').textContent = "Image inserted!";
          })
          .insertImageFromUrl(window.latestImageUrl);
      }

      document.addEventListener("DOMContentLoaded", function() {
        document.getElementById('text').addEventListener('input', updatePreview);
        document.getElementById('color').addEventListener('input', updatePreview);
        document.getElementById('bg').addEventListener('input', updatePreview);
        document.getElementById('fontSize').addEventListener('input', function() {
          document.getElementById('fontSizeValue').textContent = this.value;
          updatePreview();
        });
        document.getElementById('trimToggle').addEventListener('change', updatePreview);
        document.getElementById('fontSelect').addEventListener('change', updatePreview);
        document.getElementById('gradStart').addEventListener('input', updatePreview);
        document.getElementById('gradEnd').addEventListener('input', updatePreview);
        document.getElementById('transparentToggle').addEventListener('change', updatePreview);
        document.getElementById('insertBtn').addEventListener('click', insertIntoSlide);
      });
    </script>
  </body>
</html>
