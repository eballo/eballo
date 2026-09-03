# 📅 Weekly Summary

**📅 Start Date:** {{start_date}}
**📅 End Date:** {{end_date}}

**🕒 Total Time Spent:** {{total_time}}
**📅 Total Worked Days:** {{total_worked_days}}
**🏖️ Vacation Days:** {{vacation_days}}
**🏢 Days at Office:** {{days_at_office}}
**🏠 Days at Home:** {{days_at_home}}
**👨‍🚒 Fireman Week:** {{is_fireman_week}}

---

## 📝 General Summary

{{summary}}
{% if tickets %}
---

## 🎫 Jira Tickets

{{tickets}}
{% endif %}
{% if comparison %}
---

## 📊 vs Last Week

{{comparison}}
{% endif %}
