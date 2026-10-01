(() => {
  "use strict";
  const read = (id) => JSON.parse(document.getElementById(id).textContent);
  const categories = read("categories-data");
  const subcategories = read("subcategories-data");
  const originalCategory = read("preserved-category");
  const originalSubcategory = read("preserved-subcategory");
  const type = document.getElementById("id_type");
  const category = document.getElementById("id_category");
  const subcategory = document.getElementById("id_subcategory");

  function options(select, rows, placeholder) {
    const previous = select.value;
    select.replaceChildren(new Option(placeholder, ""));
    rows.forEach((row) => select.add(new Option(row.name + (row.is_active ? "" : " (inativa, mantida no histórico)"), row.id)));
    select.value = rows.some((row) => String(row.id) === previous) ? previous : "";
  }

  function updateSubcategories() {
    const selected = categories.find((row) => String(row.id) === category.value);
    const rows = subcategories.filter((row) => String(row.category_id) === category.value &&
      ((row.is_active && selected?.is_active) || (row.id === originalSubcategory && row.category_id === originalCategory)));
    options(subcategory, rows, selected ? "Selecione a subcategoria" : "Selecione primeiro a categoria");
  }

  function updateCategories() {
    options(category, categories.filter((row) => row.type === type.value), "Selecione a categoria");
    updateSubcategories();
  }
  type.addEventListener("change", updateCategories);
  category.addEventListener("change", updateSubcategories);
  updateCategories();
})();
