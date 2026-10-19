const STORE = "manga-tracker-read-v1";
let filter = "unread";
let data = { manga: [] };
const read = () => new Set(JSON.parse(localStorage.getItem(STORE) || "[]"));
const save = values => localStorage.setItem(STORE, JSON.stringify([...values]));

function render() {
  const seen = read();
  const root = document.querySelector("#manga-list");
  root.replaceChildren();
  let unreadCount = 0;
  for (const manga of data.manga) {
    const chapters = filter === "all" ? manga.chapters : manga.chapters.filter(c => !seen.has(c.id));
    unreadCount += manga.chapters.filter(c => !seen.has(c.id)).length;
    if (!chapters.length && filter === "unread") continue;
    const fragment = document.querySelector("#manga-template").content.cloneNode(true);
    fragment.querySelector("h2").textContent = manga.title;
    fragment.querySelector(".source").textContent = manga.site;
    const allButton = fragment.querySelector(".read-all");
    allButton.onclick = () => { manga.chapters.forEach(c => seen.add(c.id)); save(seen); render(); };
    const list = fragment.querySelector("ul");
    for (const chapter of chapters) {
      const item = document.createElement("li");
      const link = document.createElement("a"); link.href = chapter.url; link.target = "_blank"; link.rel = "noopener"; link.textContent = chapter.name;
      const button = document.createElement("button"); button.textContent = seen.has(chapter.id) ? "Read" : "Mark read";
      button.onclick = () => { seen.add(chapter.id); save(seen); render(); };
      item.append(link, button); list.append(item);
    }
    root.append(fragment);
  }
  document.querySelector("#summary").textContent = unreadCount ? `${unreadCount} unread chapter${unreadCount === 1 ? "" : "s"}` : "You’re all caught up.";
  if (!root.children.length) root.innerHTML = "<p class=empty>No unread chapters. Switch to All chapters to review your library.</p>";
}

document.querySelectorAll("nav button").forEach(button => button.onclick = () => {
  filter = button.dataset.filter;
  document.querySelectorAll("nav button").forEach(b => b.classList.toggle("active", b === button));
  render();
});
fetch("data/chapters.json", { cache: "no-store" }).then(r => r.ok ? r.json() : Promise.reject()).then(json => { data = json; render(); }).catch(() => {
  document.querySelector("#summary").textContent = "Chapter data is not available yet.";
});
