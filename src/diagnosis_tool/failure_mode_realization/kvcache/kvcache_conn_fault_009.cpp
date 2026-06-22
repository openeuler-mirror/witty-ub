#include "kvcache_conn_fault_009.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault009> g_kvcacheconnfault("kvcache_conn_fault_009");

bool KvcacheConnFault009::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = std::stoi(fields[7]);
    return (statusCode == 13);
}

std::string KvcacheConnFault009::GetName() const
{
    return "错误码13 K_NO_SPACE (OS)。";
}

std::string KvcacheConnFault009::GetRootCauseDesc() const
{
    return "磁盘空间不足，属于OS层问题（08手册:L132）。";
}

RootCause KvcacheConnFault009::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault009::GetFixSuggDesc() const
{
    return "df -h确认磁盘使用情况；检查resource.log中SPILL_HARD_DISK/SHARED_DISK字段；"
           "清理磁盘或扩容（08手册:L332）。";
}

std::string KvcacheConnFault009::GetValidationMethodDesc() const
{
    return "通过access log识别（08手册:L132, L196）：access log中status_code（第8列）为13；"
           "或df -h检查磁盘满。";
}

std::string KvcacheConnFault009::GetId() const
{
    return "kvcache_conn_fault_009";
}
} // namespace diag
