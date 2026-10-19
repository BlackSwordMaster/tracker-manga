const READ_STORE = "manga-tracker-read-v2";
const SUB_STORE = "manga-tracker-subscriptions-v2";
let filter = "unread";
let data = { feeds: [] };
const read = () => new Set(JSON.parse(localStorage.getItem(READ_STORE) || "[]"));
const subscriptions = () => new Set(JSON.parse(localStorage.getItem(SUB_STORE) || "[]"));
const save = (key, values) => localStorage.setItem(key, JSON.stringify([...values]));
const entries = () => data.feeds.flatMap(feed => feed.entries.map(entry => ({ ...entry, site: feed.name })));

function render() {
  const seen = read(), followed = subscriptions(), root = document.querySelector("#manga-list");
  root.replaceChildren();
  let unreadCount = 0;
  for (const title of followed) {
    const all = entries().filter(entry => entry.title === title);
    const chapters = filter === "all" ? all : all.filter(entry => !seen.has(entry.id));
    unreadCount += all.filter(entry => !seen.has(entry.id)).length;
    const fragment = document.querySelector("#manga-template").content.cloneNode(true);
    fragment.querySelector("h2").textContent = title;
    fragment.querySelector(".source").textContent = all[0]?.site || "Waiting for an update";
    fragment.querySelector(".read-all").onclick = () => { all.forEach(c => seen.add(c.id)); save(READ_STORE, seen); render(); };
    const list = fragment.querySelector("ul");
    if (!chapters.length) list.innerHTML = `<li class=empty>${filter === "unread" ? "You’re caught up." : "No current feed entries."}</li>`;
    for (const chapter of chapters) {
      const item = document.createElement("li"), link = document.createElement("a"), button = document.createElement("button");
      link.href = chapter.url; link.target = "_blank"; link.rel = "noopener"; link.textContent = chapter.chapter;
      button.textContent = seen.has(chapter.id) ? "Read" : "Mark read";
      button.onclick = () => { seen.add(chapter.id); save(READ_STORE, seen); render(); };
      item.append(link, button); list.append(item);
    }
    root.append(fragment);
  }
  document.querySelector("#summary").textContent = unreadCount ? `${unreadCount} unread chapter${unreadCount === 1 ? "" : "s"}` : followed.size ? "You’re all caught up." : "Add a manga to start your tracker.";
}

document.querySelector("#add-form").onsubmit = event => {
  event.preventDefault(); const input = document.querySelector("#title"), title = input.value.trim();
  const available = new Set(entries().map(entry => entry.title));
  if (!available.has(title)) { document.querySelector("#add-help").textContent = "Choose an exact title from the suggestions; it may not be in the latest feed yet."; return; }
  const followed = subscriptions(), seen = read();
  followed.add(title); entries().filter(entry => entry.title === title).forEach(entry => seen.add(entry.id));
  save(SUB_STORE, followed); save(READ_STORE, seen); input.value = ""; document.querySelector("#add-help").textContent = "Added. Current feed entries were marked read; new chapters will appear here."; render();
};
document.querySelectorAll("nav button").forEach(button => button.onclick = () => { filter = button.dataset.filter; document.querySelectorAll("nav button").forEach(b => b.classList.toggle("active", b === button)); render(); });
fetch("data/chapters.json", { cache: "no-store" }).then(r => r.ok ? r.json() : Promise.reject()).then(json => { data = json; const titles = [...new Set(entries().map(e => e.title))].sort(); document.querySelector("#titles").replaceChildren(...titles.map(title => Object.assign(document.createElement("option"), { value: title }))); render(); }).catch(() => { document.querySelector("#summary").textContent = "Chapter data is not available yet."; });
