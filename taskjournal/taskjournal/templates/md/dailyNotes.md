# 📅 Daily Tasks - {{ day_name }}

**Sprint:** {{sprint_name}}

**Date:** {{date}}
**Start Time:** {{start_time}}
**End Time:** {{end_time}}
**Break:** {{break_time}} lunch
**Time Spent:** {{time_spent}}

**Work from:** {% if work_from|lower in ["home","remote","wfh"] %}🏠 Home{% elif work_from|lower in ["office","onsite"]
%}🏢 Office{% else %}🧭 {{ work_from }}{% endif %}

---

## ✅ Planned Tasks

{{tasks}}

---

## 🔍 Code Review Tasks

{{code_review_tasks}}

---

## ✍️ Notes

{{notes}}

---
{% if firefighter %}

## 🚒 🔥 Firefighter

Priority incidents handled:

{{firefighter_notes}}

---
{% endif %}

## 📋 Summary

{{summary}}

---
{{extra}}
