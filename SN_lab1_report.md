# Лабораторная работа №1 «Первоначальная настройка git»

**Цель:** провести первоначальную настройку git, инициализировать каталог, разобраться с состояниями файлов, сделать первый коммит.

Папка репозитория: `crm/SN` (инициалы студента).

## Ход работы (Git Bash)

```bash
# 1. Создание папки и инициализация репозитория
mkdir SN
cd SN
git init
# Initialized empty Git repository in D:/MyProject/облако/crm/SN/.git/

# 2. Настройка имени и e-mail без --global (только для этого репозитория)
git config user.name "Nik1line"
git config user.email "nikolajserbatyh185@gmail.com"
git config --local --list          # проверка: user.name / user.email в локальном конфиге

# 3. Создание файла и индексация
touch my_first_file.txt
git status                         # Untracked files: my_first_file.txt
git add my_first_file.txt
git status                         # Changes to be committed: new file: my_first_file.txt

# 4. Первый коммит
git commit -m "first commit: add my_first_file.txt"
# [master (root-commit) 978f2ea] first commit: add my_first_file.txt

# 5. Изменение файла и индексация
echo "test row" >> my_first_file.txt
git status                         # Changes not staged for commit: modified: my_first_file.txt
git add my_first_file.txt

# 6. Новый файл и индексация
touch my_second_file.txt
git status                         # staged: modified my_first_file.txt; untracked: my_second_file.txt
git add my_second_file.txt
git status                         # staged: modified my_first_file.txt, new file my_second_file.txt

# 7. Второй коммит
git commit -m "second commit: add test row and my_second_file.txt"
# [master cdd2eab] second commit: add test row and my_second_file.txt

# Проверка
git log --stat
git status                         # nothing to commit, working tree clean
```

## Состояния файлов, которые были продемонстрированы

| Состояние | Когда наблюдалось |
|---|---|
| **Untracked** (неотслеживаемый) | после `touch my_first_file.txt` / `touch my_second_file.txt` |
| **Staged** (проиндексирован) | после `git add` |
| **Committed / Unmodified** (зафиксирован) | после `git commit`, `working tree clean` |
| **Modified** (изменён, не в индексе) | после добавления строки `test row` |

## Итоговая история

```
cdd2eab second commit: add test row and my_second_file.txt
978f2ea first commit: add my_first_file.txt
```
